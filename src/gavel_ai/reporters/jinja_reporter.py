"""
Jinja2-based report generator.

Provides template-based report generation using Jinja2 templating engine.
"""

from typing import Any, Dict, List

import jinja2

from gavel_ai.core.exceptions import ReporterError
from gavel_ai.models.runtime import ReporterConfig
from gavel_ai.reporters.base import Reporter


class Jinja2Reporter(Reporter):
    """
    Jinja2-based report generator.

    Renders reports using Jinja2 templates with context variables extracted
    from run data. Supports custom templates and multiple output formats.

    Per Architecture Decision 8: Pluggable report formats with clean abstraction.
    """

    def __init__(self, config: ReporterConfig):
        """
        Initialize Jinja2Reporter with configuration.

        Args:
            config: ReporterConfig with template_path and output_format
        """
        super().__init__(config)
        self.env = self._setup_jinja_env()

    def _setup_jinja_env(self) -> jinja2.Environment:
        """
        Setup Jinja2 environment with template loader.

        Returns:
            jinja2.Environment: Configured Jinja2 environment

        Raises:
            ReporterError: If template_path is invalid
        """
        try:
            loader = jinja2.FileSystemLoader(self.config.template_path)
            return jinja2.Environment(
                loader=loader,
                autoescape=jinja2.select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        except Exception as e:
            raise ReporterError(
                f"Failed to initialize template loader for path '{self.config.template_path}' - "
                f"Check template_path exists and is accessible"
            ) from e

    async def generate(self, run: Any, template: str) -> str:
        """
        Generate report from template and run data.

        Args:
            run: Run instance containing evaluation results and metadata
            template: Template filename to use for report generation

        Returns:
            str: Generated report content (HTML, Markdown, or other format)

        Raises:
            ReporterError: On template loading or rendering failures
        """
        # Build context from run data
        context = self._build_context(run)

        # Render template
        try:
            tmpl = self.env.get_template(template)
            output: str = tmpl.render(**context)
            return output
        except jinja2.TemplateNotFound as e:
            raise ReporterError(
                f"Template '{template}' not found in {self.config.template_path} - "
                f"Check template_path in config or create template file"
            ) from e
        except jinja2.TemplateSyntaxError as e:
            raise ReporterError(
                f"Template syntax error in '{template}' at line {e.lineno}: {e.message} - "
                f"Fix template syntax errors"
            ) from e
        except jinja2.UndefinedError as e:
            raise ReporterError(
                f"Undefined variable in template '{template}': {e} - "
                f"Check context variables match template requirements"
            ) from e
        except Exception as e:
            raise ReporterError(
                f"Template rendering failed for '{template}': {e} - Check template and context data"
            ) from e

    def _build_context(self, run: Any) -> Dict[str, Any]:
        """
        Build context dictionary for template rendering.

        Extracts data from Run instance and formats it for template consumption.

        Args:
            run: Run instance with metadata, results, and telemetry

        Returns:
            Dict[str, Any]: Context dictionary with template variables
        """
        # Extract metadata
        metadata = getattr(run, "metadata", {})

        # Build context with all required template variables
        context: Dict[str, Any] = {
            "title": metadata.get("eval_name", "Evaluation Report"),
            "overview": self._build_overview(run),
            "summary": self._build_summary_table(run),
            "results": self._build_results_details(run),
            "telemetry": self._extract_telemetry_metrics(run),
            "metadata": {
                "timestamp": metadata.get("timestamp", ""),
                "config_hash": metadata.get("config_hash", ""),
                "scenario_count": metadata.get("scenario_count", 0),
                "variant_count": metadata.get("variant_count", 0),
            },
        }

        # Merge custom variables if provided
        if self.config.custom_vars:
            context.update(self.config.custom_vars)

        return context

    def _build_overview(self, run: Any) -> Dict[str, Any]:
        """
        Build overview section with evaluation details.

        Args:
            run: Run instance

        Returns:
            Dict[str, Any]: Overview data
        """
        metadata = getattr(run, "metadata", {})

        return {
            "description": "Evaluation overview",
            "variant_count": metadata.get("variant_count", 0),
            "scenario_count": metadata.get("scenario_count", 0),
            "eval_type": metadata.get("eval_type", "oneshot"),
        }

    def _build_summary_table(self, run: Any) -> List[Dict[str, Any]]:
        """
        Build summary table with aggregate scores per variant.

        Args:
            run: Run instance

        Returns:
            List[Dict[str, Any]]: Summary table data
        """
        # Placeholder for now - will be fully implemented in Story 5.3
        results = getattr(run, "results", [])

        if not results:
            return []

        # Aggregate scores by variant
        variant_scores: Dict[str, List[int]] = {}

        for result in results:
            variant_id = result.get("variant_id", "unknown")
            judges = result.get("judges", [])

            if variant_id not in variant_scores:
                variant_scores[variant_id] = []

            for judge in judges:
                score = judge.get("score", 0)
                variant_scores[variant_id].append(score)

        # Build summary table
        summary = []
        for variant_id, scores in variant_scores.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                total_score = sum(scores)
            else:
                avg_score = 0
                total_score = 0

            summary.append(
                {
                    "variant_id": variant_id,
                    "avg_score": avg_score,
                    "total_score": total_score,
                    "scenario_count": len(
                        {r.get("scenario_id") for r in results if r.get("variant_id") == variant_id}
                    ),
                }
            )

        return summary

    def _build_results_details(self, run: Any) -> List[Dict[str, Any]]:
        """
        Build detailed results for each scenario.

        Args:
            run: Run instance

        Returns:
            List[Dict[str, Any]]: Detailed results data
        """
        results = getattr(run, "results", [])

        if not results:
            return []

        # Group results by scenario
        scenarios: Dict[str, List[Any]] = {}

        for result in results:
            scenario_id = result.get("scenario_id", "unknown")
            if scenario_id not in scenarios:
                scenarios[scenario_id] = []
            scenarios[scenario_id].append(result)

        # Build detailed results
        detailed_results = []

        for scenario_id, scenario_results in scenarios.items():
            # Get scenario input from first result
            scenario_input = (
                scenario_results[0].get("scenario_input", {}) if scenario_results else {}
            )

            # Build variant outputs for this scenario
            variant_outputs = []
            for result in scenario_results:
                variant_outputs.append(
                    {
                        "variant_id": result.get("variant_id", "unknown"),
                        "output": result.get("processor_output", ""),
                        "judge_results": result.get("judges", []),
                    }
                )

            detailed_results.append(
                {
                    "scenario_id": scenario_id,
                    "input": scenario_input,
                    "variant_outputs": variant_outputs,
                }
            )

        return detailed_results

    def _extract_telemetry_metrics(self, run: Any) -> Dict[str, Any]:
        """
        Extract telemetry metrics from run data.

        Args:
            run: Run instance

        Returns:
            Dict[str, Any]: Telemetry metrics
        """
        telemetry = getattr(run, "telemetry", {})

        return {
            "total_duration_seconds": telemetry.get("total_duration_seconds", 0),
            "llm_calls": telemetry.get("llm_calls", {}),
        }
