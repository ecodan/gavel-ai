"""
ScriptInputProcessor: launches subprocess scripts to evaluate external systems.

Implements the three-seam ADR-10 structure:
  - _build_request_document : outbound JSON payload construction
  - _run_subprocess          : wire transport (asyncio subprocess)
  - _parse_response_document : inbound response interpretation → ExternalResponseEnvelope

Outcomes are classified via classify_external_outcome and surfaced through
ProcessorResult.error / metadata["external_tier"] so the caller's
should_halt path does not need to re-derive the tier.
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.core.issue_classifier import (
    ExternalOutcome,
    classify_external_outcome,
)
from gavel_ai.log_config import create_logger
from gavel_ai.models.runtime import (
    ExternalIssue,
    ExternalResponseEnvelope,
    ProcessorConfig,
    ProcessorResult,
    ScriptSystemInput,
)
from gavel_ai.processors.base import InputProcessor
from gavel_ai.telemetry import get_current_run_id, get_tracer

logger = create_logger(__name__)

# Max bytes to capture from stdout/stderr to avoid unbounded memory growth
_MAX_CAPTURE_BYTES: int = 4096


class ScriptInputProcessor(InputProcessor):
    """
    Process inputs by launching subprocess scripts (external systems).

    Accepts ScriptSystemInput with command, request_payload, and filenames.
    Classifies outcomes via classify_external_outcome and propagates them
    through ProcessorResult rather than raising exceptions, so the pipeline's
    error_policy.should_halt path controls halting behaviour.
    """

    def __init__(self, config: ProcessorConfig, **kwargs: Any) -> None:
        """
        Args:
            config: ProcessorConfig with timeout/parallelism settings.
            abort_on_exec_failure: Halt on PROCESS_FAILURE (default True).
            abort_on_process_error: Halt on PROCESS_SUCCESS_WITH_ISSUE (default False).
            adapter: Outcome-classifier adapter key (default: "gavel").
        """
        super().__init__(config)
        self.tracer = get_tracer(__name__)
        self.abort_on_exec_failure: bool = bool(kwargs.get("abort_on_exec_failure", True))
        self.abort_on_process_error: bool = bool(kwargs.get("abort_on_process_error", False))
        self.adapter: str = str(kwargs.get("adapter", "gavel"))

    # ------------------------------------------------------------------
    # Seam 1: outbound request document construction
    # ------------------------------------------------------------------

    def _build_request_document(self, input_item: ScriptSystemInput) -> Dict[str, Any]:
        """Build the JSON dict to write to the request document.

        Merges the scenario's request_payload with a trace_id field so the
        external script can correlate its response with the gavel run.

        Args:
            input_item: ScriptSystemInput with fully-specified request_payload.

        Returns:
            Dict ready for json.dumps → request document file.
        """
        payload: Dict[str, Any] = dict(input_item.request_payload)
        trace_id = get_current_run_id()
        if trace_id:
            payload["trace_id"] = trace_id
        return payload

    # ------------------------------------------------------------------
    # Seam 2: wire transport (subprocess)
    # ------------------------------------------------------------------

    async def _run_subprocess(
        self,
        command: List[str],
        tmpdir: str,
        timeout: int,
    ) -> Tuple[int, str, str]:
        """Launch the script, await completion within timeout, and capture output.

        Args:
            command: Argument-list command (no shell interpolation).
            tmpdir: Working directory for the subprocess.
            timeout: Seconds to allow before SIGTERM→SIGKILL.

        Returns:
            Tuple of (returncode, stdout_text, stderr_text).

        Raises:
            ProcessorError: If the subprocess could not be launched.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                cwd=tmpdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except (OSError, FileNotFoundError) as exc:
            raise ProcessorError(
                f"Failed to launch subprocess command {command}: {exc} - "
                "Verify the command exists and is executable"
            ) from exc

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(timeout),
            )
            returncode: int = proc.returncode if proc.returncode is not None else -1
        except asyncio.TimeoutError:
            # SIGTERM first, then SIGKILL
            try:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
            except (OSError, ProcessLookupError):
                pass
            return -1, "", f"Process timed out after {timeout}s"

        # Bound captured output
        stdout_text = (stdout_bytes or b"").decode("utf-8", errors="replace")[:_MAX_CAPTURE_BYTES]
        stderr_text = (stderr_bytes or b"").decode("utf-8", errors="replace")[:_MAX_CAPTURE_BYTES]
        return returncode, stdout_text, stderr_text

    # ------------------------------------------------------------------
    # Seam 3: inbound response document parsing
    # ------------------------------------------------------------------

    def _parse_response_document(
        self,
        tmpdir: str,
        response_filename: str,
    ) -> ExternalResponseEnvelope:
        """Read and validate the response document from the temp directory.

        Enforces path confinement: the response file must reside within tmpdir.

        Args:
            tmpdir: Absolute path to the temporary directory.
            response_filename: Filename (relative) of the response document.

        Returns:
            Validated ExternalResponseEnvelope.

        Raises:
            ProcessorError: If the path escapes tmpdir, file is missing, or
                            the document fails validation.
        """
        tmpdir_path = Path(tmpdir).resolve()
        candidate = (tmpdir_path / response_filename).resolve()

        # Append os.sep to prevent a sibling directory like /tmp/tmpABCEXTRA
        # from passing a prefix check against /tmp/tmpABC.
        if not str(candidate).startswith(str(tmpdir_path) + os.sep):
            raise ProcessorError(
                f"response_filename '{response_filename}' resolves to '{candidate}' "
                f"which is outside the expected boundary '{tmpdir_path}' - "
                "Path traversal not allowed"
            )

        if not candidate.exists():
            raise ProcessorError(
                f"Response document not found at '{candidate}' - "
                "Verify the script writes a response document before exiting"
            )

        try:
            raw = json.loads(candidate.read_text(encoding="utf-8"))
            return ExternalResponseEnvelope.model_validate(raw)
        except json.JSONDecodeError as exc:
            raise ProcessorError(
                f"Response document at '{candidate}' is not valid JSON: {exc} - "
                "Verify the script writes well-formed JSON"
            ) from exc
        except Exception as exc:
            raise ProcessorError(
                f"Response document at '{candidate}' failed schema validation: {exc} - "
                "Ensure the response document matches the ExternalResponseEnvelope schema"
            ) from exc

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def process(self, inputs: List[ScriptSystemInput]) -> ProcessorResult:  # type: ignore[override]
        """
        Execute batch of ScriptSystemInput via subprocess.

        Returns ProcessorResult with error/metadata["external_tier"] populated for
        non-OK outcomes rather than raising, so the caller's should_halt path applies.
        """
        all_outputs: List[str] = []
        aggregated_metadata: Dict[str, Any] = {
            "total_latency_ms": 0,
            "input_count": len(inputs),
            "trace_id": get_current_run_id() or "",
        }

        for input_item in inputs:
            with tempfile.TemporaryDirectory() as tmpdir:
                start_time = time.time()

                # Write request document
                request_path = Path(tmpdir) / input_item.request_filename
                request_doc = self._build_request_document(input_item)
                request_path.write_text(json.dumps(request_doc), encoding="utf-8")

                # Run subprocess
                returncode, stdout, stderr = await self._run_subprocess(
                    input_item.command,
                    tmpdir,
                    self.config.timeout_seconds,
                )

                duration_ms = int((time.time() - start_time) * 1000)
                aggregated_metadata["total_latency_ms"] += duration_ms

                if stdout:
                    aggregated_metadata["stdout"] = stdout
                if stderr:
                    aggregated_metadata["stderr"] = stderr

                # Non-zero exit — PROCESS_FAILURE (no response doc expected)
                if returncode != 0:
                    tier = classify_external_outcome(
                        ExternalOutcome.PROCESS_FAILURE,
                        self.abort_on_exec_failure,
                        self.abort_on_process_error,
                        self.adapter,
                    )
                    aggregated_metadata.update({
                        "returncode": returncode,
                        "external_outcome": ExternalOutcome.PROCESS_FAILURE.value,
                        "external_tier": tier,
                    })
                    return ProcessorResult(
                        output="",
                        error=(
                            f"Script exited with code {returncode} - "
                            "Check stderr for details"
                        ),
                        metadata=aggregated_metadata,
                    )

                # Try to parse the response document
                try:
                    envelope = self._parse_response_document(
                        tmpdir, input_item.response_filename
                    )
                except ProcessorError as exc:
                    tier = classify_external_outcome(
                        ExternalOutcome.PROCESS_FAILURE,
                        self.abort_on_exec_failure,
                        self.abort_on_process_error,
                        self.adapter,
                    )
                    aggregated_metadata.update({
                        "returncode": returncode,
                        "external_outcome": ExternalOutcome.PROCESS_FAILURE.value,
                        "external_tier": tier,
                    })
                    return ProcessorResult(
                        output="",
                        error=str(exc),
                        metadata=aggregated_metadata,
                    )

                # envelope.status == "error" → PROCESS_FAILURE
                if envelope.status == "error":
                    tier = classify_external_outcome(
                        ExternalOutcome.PROCESS_FAILURE,
                        self.abort_on_exec_failure,
                        self.abort_on_process_error,
                        self.adapter,
                    )
                    issue_text = (
                        f"{envelope.issue.code}: {envelope.issue.message}"
                        if envelope.issue
                        else "external system reported status=error"
                    )
                    aggregated_metadata.update({
                        "returncode": returncode,
                        "external_outcome": ExternalOutcome.PROCESS_FAILURE.value,
                        "external_tier": tier,
                    })
                    if envelope.issue:
                        aggregated_metadata["issue"] = {
                            "code": envelope.issue.code,
                            "level": envelope.issue.level,
                            "message": envelope.issue.message,
                        }
                    return ProcessorResult(
                        output="",
                        error=f"External script process failure: {issue_text}",
                        metadata=aggregated_metadata,
                    )

                # issue present with status=="ok" → PROCESS_SUCCESS_WITH_ISSUE (warning-tier)
                if envelope.issue is not None:
                    tier = classify_external_outcome(
                        ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE,
                        self.abort_on_exec_failure,
                        self.abort_on_process_error,
                        self.adapter,
                    )
                    result_text = json.dumps(envelope.result) if envelope.result else ""
                    issue: ExternalIssue = envelope.issue
                    aggregated_metadata.update({
                        "returncode": returncode,
                        "external_outcome": ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE.value,
                        "external_tier": tier,
                        "issue": {
                            "code": issue.code,
                            "level": issue.level,
                            "message": issue.message,
                        },
                    })
                    return ProcessorResult(
                        output=result_text,
                        error=(
                            f"External system issue [{issue.level}] {issue.code}: "
                            f"{issue.message}"
                        ),
                        metadata=aggregated_metadata,
                    )

                # Clean success
                aggregated_metadata["returncode"] = returncode
                result_text = json.dumps(envelope.result) if envelope.result else ""
                all_outputs.append(result_text)

                if envelope.metadata:
                    aggregated_metadata.update(envelope.metadata)

        combined_output = (
            "\n\n".join(all_outputs)
            if len(all_outputs) > 1
            else (all_outputs[0] if all_outputs else "")
        )
        return ProcessorResult(output=combined_output, metadata=aggregated_metadata)
