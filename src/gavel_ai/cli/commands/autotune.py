"""Autotune evaluation workflow CLI commands."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gavel_ai.cli.common import resolve_eval_root, run_async
from gavel_ai.cli.scaffolding import generate_autotune_templates
from gavel_ai.core.contexts import LocalFileSystemEvalContext
from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.core.workflows.autotune import AutotuneWorkflow
from gavel_ai.log_config import get_application_logger
from gavel_ai.models.config import AutotuneRunSummary
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)
app_logger = get_application_logger()

app = typer.Typer(
    name="autotune",
    help="Autotune evaluation workflow commands",
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


def _print_run_summary(run_dir: Path) -> None:
    """Print a per-iteration progress table and the report path from run_summary.json."""
    summary_path = run_dir / "run_summary.json"
    run_summary = AutotuneRunSummary(**json.loads(summary_path.read_text(encoding="utf-8")))

    table = Table(title="Autotune Progress")
    table.add_column("Iteration", justify="right")
    table.add_column("Prompt", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("Improvement", justify="right")
    table.add_column("Converged", justify="center")

    for iteration in run_summary.iterations:
        is_best = iteration.iteration == run_summary.best_iteration
        style = "bold green" if is_best else None
        table.add_row(
            str(iteration.iteration),
            iteration.prompt_version,
            f"{iteration.score:.3f}",
            f"{iteration.improvement:+.3f}",
            iteration.convergence_reason or ("yes" if iteration.converged else ""),
            style=style,
        )

    console.print(table)
    console.print("\n[bold green]✅ Autotune run complete[/bold green]")
    console.print(f"   Run ID: [cyan]{run_summary.run_id}[/cyan]")
    console.print(
        f"   Best iteration: [cyan]{run_summary.best_iteration}[/cyan] "
        f"(score: {run_summary.best_score:.3f})"
    )
    console.print(f"   Final score: [cyan]{run_summary.final_score:.3f}[/cyan]")
    console.print(f"   Convergence: [cyan]{run_summary.convergence_reason or 'n/a'}[/cyan]")
    console.print(f"   Report: {run_dir / 'report.html'}")


@app.command()
def create(
    eval: str = typer.Option(..., "--eval", help="Evaluation name"),
    eval_root: _EvalRootArg = None,
    force: bool = typer.Option(False, "--force", help="Overwrite an existing evaluation directory"),
) -> None:
    """Create a new autotune evaluation scaffold."""
    try:
        if not eval.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                f"Invalid evaluation name '{eval}' - "
                "Use only alphanumeric characters, hyphens, and underscores"
            )

        eval_root_path: Path = resolve_eval_root(eval_root)
        eval_path = eval_root_path / eval

        if eval_path.exists() and not force:
            raise ConfigError(
                f"Evaluation '{eval}' already exists - "
                "Use a different name, delete the existing evaluation, or pass --force"
            )

        generate_autotune_templates(eval_root_path, eval)

        app_logger.info(f"Autotune evaluation '{eval}' created at {eval_path}")

        typer.echo(f"✅ Created autotune evaluation '{eval}' at {eval_path}")
        typer.echo(f"   Location: {eval_path.absolute()}")
        typer.echo("\nNext steps:")
        typer.echo(f"  1. Add scenarios to {eval_path / 'data' / 'scenarios.json'}")
        typer.echo(f"  2. Edit the seed prompt in {eval_path / 'config' / 'prompts' / f'{eval}.toml'}")
        typer.echo(f"  3. Review the 'tuning' block in {eval_path / 'config' / 'eval_config.json'}")
        typer.echo(f"  4. Run: gavel autotune run --eval {eval}")
    except (ConfigError, ValidationError) as e:
        app_logger.error(f"Failed to create autotune evaluation '{eval}': {e}", exc_info=True)
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command()
def run(
    eval_name: str = typer.Option(..., "--eval", help="Evaluation name"),
    run_id: Optional[str] = typer.Option(None, "--run", help="Run ID to resume"),
    eval_root: _EvalRootArg = None,
) -> None:
    """CLI entry point for the AutotuneWorkflow (run or resume)."""
    app_logger.info(f"Autotune evaluation '{eval_name}' started")

    resolved_root: Path = resolve_eval_root(eval_root)
    eval_ctx = LocalFileSystemEvalContext(eval_name=eval_name, eval_root=resolved_root)

    workflow = AutotuneWorkflow(eval_ctx, app_logger)
    try:
        run_ctx = run_async(workflow.execute(resume_run_id=run_id))

        verb = "Resumed" if run_id else "Created"
        typer.echo(f"✓ {verb} run: {run_ctx.run_id}")
        typer.echo("✓ Completed validation")
        typer.echo("✓ Completed autotune_iteration")
        typer.echo("✓ Completed reporting")

        _print_run_summary(run_ctx.run_dir)

    except Exception as e:
        log_path = (workflow.run_ctx.run_dir / "run.log") if workflow.run_ctx else None
        _print_run_error(e, log_path)
        raise typer.Exit(code=1) from None


__all__ = ["app"]
