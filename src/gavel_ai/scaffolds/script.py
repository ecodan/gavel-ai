"""
ScriptSystemUnderTest — Script (subprocess + temp-dir) transport scaffold.

Provides glue for building a Python script that Gavel launches as a subprocess.
The script reads ``request.json`` from the current working directory (temp dir),
calls ``handle``, and writes ``response.json`` back.

Subclass this and implement ``handle(request) -> result``, then call
``ScriptSystemUnderTest().main()`` from your script's ``__main__`` block.

This module does NOT import from gavel_ai.core.*.
See: docs/specs/schema-external-runner.md
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

from gavel_ai.scaffolds.base import ScaffoldValidationError, _BaseSystemUnderTest, _logger
from gavel_ai.models.runtime import ExternalResponseEnvelope


class ScriptSystemUnderTest(_BaseSystemUnderTest):
    """
    Script-transport scaffold for an external system under test.

    Gavel writes ``request.json`` to a temp dir and launches the script with
    that dir as cwd.  After the script exits 0, Gavel reads ``response.json``
    from the same dir.

    Subclasses implement ``handle(request) -> result`` and call ``main()``
    from their ``if __name__ == "__main__"`` block.

    Example::

        from gavel_ai.scaffolds import ScriptSystemUnderTest
        from gavel_ai.models.runtime import ExternalTaskRequest

        class MyScript(ScriptSystemUnderTest):
            def handle(self, request: ExternalTaskRequest):
                return {"output": call_my_model(request.rendered_prompt)}

        if __name__ == "__main__":
            MyScript().main()
    """

    #: File name written/read by Gavel (matches ScriptSystemInput defaults).
    REQUEST_FILENAME: str = "request.json"
    RESPONSE_FILENAME: str = "response.json"

    def main(
        self,
        request_path: str = REQUEST_FILENAME,
        response_path: str = RESPONSE_FILENAME,
    ) -> None:
        """Script entry-point: read request, process, write response, exit.

        Args:
            request_path: Path to request.json (relative to cwd or absolute).
            response_path: Path where response.json should be written.
        """
        req_file = Path(request_path)
        resp_file = Path(response_path)

        try:
            raw: Dict[str, Any] = json.loads(req_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            _logger.error("request file not found: %s", req_file)
            sys.exit(1)
        except json.JSONDecodeError as exc:
            _logger.error("request file is not valid JSON: %s", exc)
            sys.exit(1)

        try:
            envelope: ExternalResponseEnvelope = self.process(raw)
        except ScaffoldValidationError as exc:
            _logger.error("scaffold validation error: %s", exc)
            sys.exit(1)

        resp_file.write_text(envelope.model_dump_json(), encoding="utf-8")
        sys.exit(0)
