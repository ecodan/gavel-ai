"""OneShot evaluation workflow CLI commands."""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gavel_ai.cli.common import resolve_eval_root, run_async
from gavel_ai.cli.scaffolding import generate_all_templates
from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.exceptions import ConfigError, ResourceNotFoundError, ValidationError
from gavel_ai.core.run_metrics import RunMetrics, compute_run_metrics
from gavel_ai.core.steps.judge_runner import JudgeRunnerStep
from gavel_ai.core.steps.report_runner import ReportRunnerStep
from gavel_ai.core.workflows.oneshot import OneShotWorkflow
from gavel_ai.log_config import get_application_logger
from gavel_ai.models.runtime import OutputRecord, ReporterConfig
from gavel_ai.reporters.oneshot_reporter import OneShotReporter
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)
app_logger = get_application_logger()

app = typer.Typer(
    name="oneshot",
    help="OneShot evaluation workflow commands",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

_EVAL_ROOT_HELP = "Root directory containing evaluations (default: .gavel/evaluations)"
_EvalRootArg = Annotated[
    Optional[str], typer.Option("--eval-root", envvar="GAVEL_EVAL_ROOT", help=_EVAL_ROOT_HELP)
]


def _print_run_error(e: Exception, log_path: Optional[Path] = None) -> None:
    """Print a human-readable error panel to stderr; full trace goes to the log."""
    cause = e.__cause__ or e
    msg = Text(str(cause), style="red")
    hint = f"\n\nSee [bold]{log_path}[/bold] for the full stack trace." if log_path else ""
    err_console.print(
        Panel(
            msg.__str__() + hint,
            title="[bold red]Run failed[/bold red]",
            border_style="red",
            expand=False,
        )
    )


def _get_eval_dir(
    eval_name: Optional[str],
    run_id: Optional[str] = None,
    eval_root: Optional[Path] = None,
) -> tuple[str, Path]:
    """Discover evaluation directory given eval name or run_id."""
    root: Path = eval_root if eval_root is not None else resolve_eval_root(None)

    if eval_name:
        eval_path = root / eval_name
        if not eval_path.exists():
            raise ResourceNotFoundError(f"Evaluation '{eval_name}' not found")
        return eval_name, eval_path

    if not run_id:
        raise ConfigError("Must provide either --eval or --run")

    if not root.exists():
        raise ConfigError("No evaluations found. Use 'gavel oneshot create' first.")

    for eval_dir in root.iterdir():
        if eval_dir.is_dir() and (eval_dir / "runs" / run_id).exists():
            return eval_dir.name, eval_dir

    raise ResourceNotFoundError(f"Run ID '{run_id}' not found in any evaluation")


def _print_run_summary(run_ctx: LocalRunContext, eval_ctx: LocalFileSystemEvalContext) -> None:
    eval_config = eval_ctx.eval_config.read()
    scenarios = eval_ctx.scenarios.read()

    judge_count = sum(
        len(subject.judges) for subject in (eval_config.test_subjects or []) if subject.judges
    )

    console.print("\n[bold green]✅ Evaluation complete[/bold green]")
    console.print(f"   Run ID: [cyan]{run_ctx.run_id}[/cyan]")
    console.print(f"   Scenarios: [cyan]{len(scenarios)}[/cyan]")
    if judge_count > 0:
        console.print(f"   Judges: [cyan]{judge_count}[/cyan]")
    console.print(f"   Report: {run_ctx.run_dir / 'report.html'}")


VALID_TEMPLATES = ("default", "classification", "regression", "conversational")
VALID_TYPES = ("local", "in-situ", "external")


@app.command()
def create(
    eval: str = typer.Option(..., "--eval", help="Evaluation name"),
    type: str = typer.Option(
        "local",
        "--type",
        help=(
            "Evaluation type: local, in-situ, or external. "
            "'external' scaffolds a closed-box target driven by an out-of-process "
            "system under test (script and http transport variants both generated)."
        ),
    ),
    template: str = typer.Option(
        "default",
        "--template",
        help=(
            "Scaffold template: default, classification, regression, conversational. "
            "Recommended judge thresholds — "
            "toxicity/hallucination: 0.85-0.95; "
            "answer_relevancy/faithfulness: 0.65-0.80; "
            "conversation_completeness: 0.70-0.85."
        ),
    ),
    eval_root: _EvalRootArg = None,
) -> None:
    """Create a new evaluation scaffold."""
    try:
        if not eval.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                f"Invalid evaluation name '{eval}' - "
                "Use only alphanumeric characters, hyphens, and underscores"
            )

        if template not in VALID_TEMPLATES:
            raise ValidationError(
                f"Unknown template '{template}' - Available: {', '.join(VALID_TEMPLATES)}"
            )

        if type not in VALID_TYPES:
            raise ValidationError(
                f"Unknown evaluation type '{type}' - Available: {', '.join(VALID_TYPES)}"
            )

        eval_root_path: Path = resolve_eval_root(eval_root)
        eval_path = eval_root_path / eval

        if eval_path.exists():
            raise ConfigError(
                f"Evaluation '{eval}' already exists - "
                "Use different name or delete existing evaluation"
            )

        generate_all_templates(eval_root_path, eval, type, template)

        app_logger.info(f"Evaluation '{eval}' created at {eval_path}")

        typer.echo(f"✅ Created evaluation '{eval}' at {eval_path}")
        typer.echo(f"   Type: {type}")
        typer.echo(f"   Location: {eval_path.absolute()}")
        typer.echo("\nNext steps:")
        typer.echo(f"  1. Edit config files in {eval_path / 'config'}")
        typer.echo(f"  2. Add scenarios to {eval_path / 'data'}")
        typer.echo(f"  3. Run: gavel oneshot run --eval {eval}")
    except (ConfigError, ValidationError) as e:
        app_logger.error(f"Failed to create evaluation '{eval}': {e}", exc_info=True)
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command()
def run(
    eval_name: str = typer.Option(..., "--eval", help="Evaluation name"),
    scenarios: Optional[str] = typer.Option(
        None, "--scenarios", help="Scenario filter (e.g., 1-10)"
    ),
    eval_root: _EvalRootArg = None,
) -> None:
    """CLI entry point for OneShot evaluation workflow."""
    app_logger.info(f"OneShot Evaluation '{eval_name}' started")

    resolved_root: Path = resolve_eval_root(eval_root)
    eval_ctx = LocalFileSystemEvalContext(eval_name=eval_name, eval_root=resolved_root)

    workflow = OneShotWorkflow(eval_ctx, app_logger)
    try:
        run_ctx = run_async(workflow.execute())

        typer.echo(f"✓ Created run: {run_ctx.run_id}")
        typer.echo("✓ Completed validation")
        typer.echo("✓ Completed scenario_processing")
        typer.echo("✓ Completed judging")
        typer.echo("✓ Completed reporting")

        _print_run_summary(run_ctx, eval_ctx)

    except Exception as e:
        log_path = (workflow.run_ctx.run_dir / "run.log") if workflow.run_ctx else None
        _print_run_error(e, log_path)
        raise typer.Exit(code=1) from None


@app.command()
def judge(
    run_id: str = typer.Option(..., "--run", help="Run ID to judge"),
    eval_name: Optional[str] = typer.Option(None, "--eval", help="Evaluation name"),
    eval_root: _EvalRootArg = None,
) -> None:
    """Judge evaluation results using pipeline steps."""
    try:
        resolved_root: Path = resolve_eval_root(eval_root)
        real_eval_name, eval_dir = _get_eval_dir(eval_name, run_id, resolved_root)
        eval_ctx = LocalFileSystemEvalContext(eval_name=real_eval_name, eval_root=resolved_root)
        run_ctx = LocalRunContext(
            eval_ctx=eval_ctx,
            base_dir=eval_dir / "runs",
            run_id=run_id,
            snapshot=False,
        )

        console.print(f"Loading processor outputs from run '{run_id}'")

        records: List[OutputRecord] = list(run_ctx.results_raw.read())
        if not records:
            raise ResourceNotFoundError(
                f"No results found for run '{run_id}'. Did it finish processing?"
            )

        run_ctx.processor_results = records

        run_async(JudgeRunnerStep(app_logger).execute(run_ctx))
        run_async(ReportRunnerStep(app_logger).execute(run_ctx))

        console.print(
            f"[bold green]✓ Completed judging ({len(records)} results processed)[/bold green]"
        )

    except (ConfigError, ResourceNotFoundError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


def _print_run_metrics(run_id: str, metrics: RunMetrics) -> None:
    table = Table(title=f"Run metrics: {run_id}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    def _fmt(value: Optional[float], suffix: str = "") -> str:
        return f"{value:.1f}{suffix}" if value is not None else "n/a"

    table.add_row("Scenarios", str(metrics.scenario_count))
    table.add_row("Success", str(metrics.success_count))
    table.add_row("Errors", str(metrics.error_count))
    table.add_row("Error rate", f"{metrics.error_rate * 100:.1f}%")
    table.add_row("Latency avg", _fmt(metrics.latency_avg_ms, " ms"))
    table.add_row("Latency p50", _fmt(metrics.latency_p50_ms, " ms"))
    table.add_row("Latency p95", _fmt(metrics.latency_p95_ms, " ms"))
    table.add_row("Throughput", _fmt(metrics.throughput_per_sec, " records/sec"))
    table.add_row("Prompt tokens", str(metrics.tokens_prompt_total))
    table.add_row("Completion tokens", str(metrics.tokens_completion_total))

    console.print(table)


@app.command()
def analyze(
    run_id: str = typer.Option(..., "--run", help="Run ID to analyze"),
    eval_name: Optional[str] = typer.Option(None, "--eval", help="Evaluation name"),
    eval_root: _EvalRootArg = None,
) -> None:
    """Compute performance metrics (latency, throughput, error rate, tokens) for a run.

    Transport-agnostic — works for prompt-based, script, and http external SUT runs alike,
    since all populate the same OutputRecord fields in results_raw.jsonl.
    """
    try:
        resolved_root: Path = resolve_eval_root(eval_root)
        real_eval_name, eval_dir = _get_eval_dir(eval_name, run_id, resolved_root)
        eval_ctx = LocalFileSystemEvalContext(eval_name=real_eval_name, eval_root=resolved_root)
        run_ctx = LocalRunContext(
            eval_ctx=eval_ctx,
            base_dir=eval_dir / "runs",
            run_id=run_id,
            snapshot=False,
        )

        records: List[OutputRecord] = list(run_ctx.results_raw.read())
        if not records:
            raise ResourceNotFoundError(
                f"No results found for run '{run_id}'. Did it finish processing?"
            )

        metrics = compute_run_metrics(records)
        _print_run_metrics(run_id, metrics)

    except (ConfigError, ResourceNotFoundError, ValidationError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


def _generate_report(
    run_id: str,
    eval_name: Optional[str],
    template: Optional[str],
    eval_root: Optional[Path] = None,
) -> None:
    resolved_root: Path = eval_root if eval_root is not None else resolve_eval_root(None)
    real_eval_name, eval_dir = _get_eval_dir(eval_name, run_id, resolved_root)

    eval_ctx = LocalFileSystemEvalContext(eval_name=real_eval_name, eval_root=resolved_root)
    run_ctx = LocalRunContext(
        eval_ctx=eval_ctx,
        base_dir=eval_dir / "runs",
        run_id=run_id,
        snapshot=False,
    )

    if not run_ctx.run_dir.exists():
        raise ResourceNotFoundError(f"Run directory not found: {run_ctx.run_dir}")

    typer.echo(f"Generating report for run '{run_id}' in evaluation '{real_eval_name}'...")

    results = []
    if run_ctx.results_judged.exists():
        results = list(run_ctx.results_judged.read())
    elif run_ctx.results_raw.exists():
        results = list(run_ctx.results_raw.read())
    else:
        raise ConfigError(f"No results found for run {run_id}")

    metadata: Dict[str, Any] = {}
    if run_ctx.run_metadata.exists():
        metadata_obj = run_ctx.run_metadata.read()
        if hasattr(metadata_obj, "model_dump"):
            metadata = metadata_obj.model_dump()
        else:
            metadata = metadata_obj
    else:
        metadata = {
            "eval_name": real_eval_name,
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "unknown",
        }

    templates_dir = Path(__file__).parent.parent.parent / "reporters" / "templates"
    reporter_config = ReporterConfig(
        template_path=str(templates_dir),
        output_format="html",
    )
    reporter = OneShotReporter(reporter_config)

    class ReportData:
        def __init__(self, metadata: dict, results: list, run_id: str) -> None:
            self.metadata = metadata
            self.results = results
            self.run_id = run_id

    report_data = ReportData(metadata, results, run_id)
    template_name = template if template else "oneshot.html"

    report_content = run_async(reporter.generate(report_data, template_name))

    report_path = run_ctx.run_dir / "report.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    typer.echo(f"✅ Report generated: {report_path.absolute()}")


@app.command()
def report(
    run_id: str = typer.Option(..., "--run", help="Run ID to report"),
    eval_name: Optional[str] = typer.Option(None, "--eval", help="Evaluation name"),
    template: Optional[str] = typer.Option(None, "--template", help="Custom report template"),
    eval_root: _EvalRootArg = None,
) -> None:
    """Generate evaluation report."""
    try:
        _generate_report(run_id, eval_name, template, resolve_eval_root(eval_root))
    except ConfigError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command(name="list")
def list_runs(
    eval_name: Optional[str] = typer.Option(None, "--eval", help="Evaluation name to filter"),
    eval_root: _EvalRootArg = None,
) -> None:
    """List evaluation runs."""
    try:
        resolved_root: Path = resolve_eval_root(eval_root)
        evals_to_check: List[Path] = []
        if eval_name:
            _, eval_dir = _get_eval_dir(eval_name, eval_root=resolved_root)
            evals_to_check = [eval_dir]
        else:
            if not resolved_root.exists():
                raise ConfigError("No evaluations found. Use 'gavel oneshot create' first.")
            evals_to_check = [d for d in resolved_root.iterdir() if d.is_dir()]

        table = Table(title="Evaluation Runs")
        table.add_column("Run ID", style="cyan", no_wrap=True)
        table.add_column("Eval", style="magenta", no_wrap=True)
        table.add_column("Timestamp", style="green")
        table.add_column("Scenarios", justify="right")
        table.add_column("Milestone", justify="center", no_wrap=True)

        has_runs = False
        for eval_dir in evals_to_check:
            runs_dir = eval_dir / "runs"
            if not runs_dir.exists():
                continue

            for run_dir in sorted(runs_dir.iterdir(), key=lambda d: d.name, reverse=True):
                if not run_dir.is_dir():
                    continue
                has_runs = True

                metadata_file = run_dir / "manifest.json"
                timestamp = "Unknown"
                scenarios = "Unknown"
                milestone = ""

                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            data = json.load(f)
                        timestamp = data.get("timestamp", "").split(".")[0].replace("T", " ")
                        scenarios = str(data.get("scenario_count", "Unknown"))
                        is_milestone = data.get("is_milestone", False)
                        comment = data.get("milestone_comment", "")
                        if is_milestone:
                            milestone = f"⭐ {comment}" if comment else "⭐"
                    except Exception:
                        pass

                table.add_row(run_dir.name, eval_dir.name, timestamp, scenarios, milestone)

        if not has_runs:
            if eval_name:
                console.print(f"No runs found for evaluation '{eval_name}'")
            else:
                console.print("No runs found")
        else:
            console.print(table)

    except (ConfigError, ResourceNotFoundError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command()
def milestone(
    run_id: str = typer.Option(..., "--run", help="Run ID to mark as milestone"),
    eval_name: Optional[str] = typer.Option(None, "--eval", help="Evaluation name"),
    comment: Optional[str] = typer.Option(None, "--comment", help="Milestone comment"),
    remove: bool = typer.Option(False, "--remove", help="Remove milestone status"),
    eval_root: _EvalRootArg = None,
) -> None:
    """Mark run as milestone."""
    try:
        resolved_root: Path = resolve_eval_root(eval_root)
        eval_name, eval_dir = _get_eval_dir(eval_name, run_id, resolved_root)
        run_dir = eval_dir / "runs" / run_id
        metadata_file = run_dir / "manifest.json"

        if not metadata_file.exists():
            raise ResourceNotFoundError(f"Manifest not found for run '{run_id}'")

        with open(metadata_file, "r") as f:
            data = json.load(f)

        if remove:
            data["is_milestone"] = False
            data["milestone_comment"] = None
            data["milestone_timestamp"] = None
            action = "removed from milestones"
        else:
            data["is_milestone"] = True
            data["milestone_comment"] = comment
            data["milestone_timestamp"] = datetime.now(timezone.utc).isoformat()
            action = f"marked as milestone{f' ({comment})' if comment else ''}"

        with open(metadata_file, "w") as f:
            json.dump(data, f, indent=2)

        console.print(f"[bold green]✅ Run {run_id}[/bold green] {action}")

    except (ConfigError, ResourceNotFoundError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
