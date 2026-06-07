"""AutotuneReportingStep: renders the autotune report from the persisted run summary.

Reads runs/<id>/run_summary.json (written by AutotuneIterationStep) and the
best-scoring prompt version's text from prompts.toml, then renders
autotune.html via AutotuneReporter.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

import toml

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.models.config import AutotuneRunSummary
from gavel_ai.models.runtime import ReporterConfig
from gavel_ai.reporters.autotune_reporter import AutotuneReporter, AutotuneRunData


class AutotuneReportingStep(Step):
    """Renders runs/<id>/report.html from the persisted AutotuneRunSummary."""

    def __init__(self, logger: logging.Logger):
        super().__init__(logger)

    @property
    def phase(self) -> StepPhase:
        return StepPhase.REPORTING

    async def execute(self, context: RunContext) -> None:
        """
        Raises:
            ConfigError: If run_summary.json (written by AutotuneIterationStep) is missing.
        """
        run_dir: Path = context.run_dir
        summary_path = run_dir / "run_summary.json"
        if not summary_path.exists():
            raise ConfigError(
                f"AutotuneReportingStep requires {summary_path} - "
                "Run AutotuneIterationStep first"
            )

        run_summary = AutotuneRunSummary(**self._load_json(summary_path))

        prompts_toml_path = run_dir / "prompts.toml"
        best_version = f"v{run_summary.best_iteration}"
        prompts_data: Dict[str, Any] = toml.load(str(prompts_toml_path))
        best_prompt_text: str = prompts_data.get(best_version, {}).get("prompt", "")

        run_data = AutotuneRunData(
            run_summary=run_summary,
            best_prompt_text=best_prompt_text,
            prompts_toml_path=f"runs/{run_summary.run_id}/prompts.toml",
        )

        templates_dir = Path(__file__).parent.parent.parent / "reporters" / "templates"
        reporter = AutotuneReporter(ReporterConfig(template_path=str(templates_dir), output_format="html"))
        report_content = await reporter.generate(run_data, "autotune.html")

        report_path = run_dir / "report.html"
        report_path.write_text(report_content, encoding="utf-8")
        self.logger.info(f"Autotune report written to {report_path}")

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))


__all__ = ["AutotuneReportingStep"]
