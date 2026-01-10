"""OneShot evaluation workflow CLI commands."""

import asyncio
from pathlib import Path
from typing import Optional

import typer

from gavel_ai.cli.scaffolding import generate_all_templates
from gavel_ai.core.contexts import LocalFileSystemEvalContext
from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.core.workflows.oneshot import OneShotWorkflow
from gavel_ai.log_config import get_application_logger
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)
app_logger = get_application_logger()

DEFAULT_EVAL_ROOT = Path(".gavel/evaluations")

app = typer.Typer(
    name="oneshot",
    help="OneShot evaluation workflow commands",
    add_completion=False,
)


@app.command()
def create(
    eval: str = typer.Option(..., "--eval", help="Evaluation name"),
    type: str = typer.Option("local", "--type", help="Evaluation type: local or in-situ"),
    eval_root: Optional[str] = typer.Option(
        None, "--eval-root", help="Custom evaluation root directory"
    ),
) -> None:
    """Create a new evaluation scaffold."""
    try:
        # Validate evaluation name
        if not eval.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                f"Invalid evaluation name '{eval}' - "
                "Use only alphanumeric characters, hyphens, and underscores"
            )

        # Determine eval root directory
        eval_root_path: Path = Path(eval_root) if eval_root else Path(DEFAULT_EVAL_ROOT)
        eval_path = eval_root_path / eval

        # Check if evaluation already exists
        if eval_path.exists():
            raise ConfigError(
                f"Evaluation '{eval}' already exists - "
                "Use different name or delete existing evaluation"
            )

        # Generate all templates
        generate_all_templates(eval_root_path, eval, type)

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
) -> None:
    """CLI entry point for OneShot evaluation workflow."""
    app_logger.info(f"OneShot Evaluation '{eval_name}' started")

    # Create evaluation context
    eval_ctx = LocalFileSystemEvalContext(eval_name=eval_name, eval_root=DEFAULT_EVAL_ROOT)

    try:
        # Call business logic (core tier) - run async workflow
        workflow = OneShotWorkflow(eval_ctx, app_logger)
        run_ctx = asyncio.run(workflow.execute())

        # Format output for CLI (presentation tier)
        typer.echo(f"✓ Created run: {run_ctx.run_id}")
        typer.echo("✓ Completed validation")
        typer.echo("✓ Completed scenario_processing")
        typer.echo("✓ Completed judging")
        typer.echo("✓ Completed reporting")

        # Print summary
        report_path = run_ctx.run_dir / "report.html"

        # Read eval config to get statistics
        eval_config = eval_ctx.eval_config.read()
        scenarios = eval_ctx.scenarios.read()
        scenario_count = len(scenarios)

        # Count judges from test_subjects
        judge_count = 0
        if eval_config.test_subjects:
            for subject in eval_config.test_subjects:
                if subject.judges:
                    judge_count += len(subject.judges)

        typer.echo("\n✅ Evaluation complete")
        typer.echo(f"   Run ID: {run_ctx.run_id}")
        typer.echo(f"   Scenarios: {scenario_count}")
        if judge_count > 0:
            typer.echo(f"   Judges: {judge_count}")
        typer.echo(f"   Report: {report_path.absolute()}")

    except (ConfigError, ValidationError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command()
def judge(
    run_id: str = typer.Option(..., "--run", help="Run ID to judge"),
    judges: Optional[str] = typer.Option(None, "--judges", help="Comma-separated judge names"),
) -> None:
    """Judge evaluation results."""
    typer.echo(f"Judging run '{run_id}'")
    typer.echo("Implementation pending - see Epic 4")


@app.command()
def report(
    run_id: str = typer.Option(..., "--run", help="Run ID to report"),
    template: Optional[str] = typer.Option(None, "--template", help="Custom report template"),
) -> None:
    """Generate evaluation report."""
    typer.echo(f"Generating report for run '{run_id}'")
    typer.echo("Implementation pending - see Epic 5")


@app.command()
def list(
    eval: Optional[str] = typer.Option(None, "--eval", help="Evaluation name to filter"),
) -> None:
    """List evaluation runs."""
    typer.echo("Listing evaluation runs")
    typer.echo("Implementation pending - see Epic 6")


@app.command()
def milestone(
    run_id: str = typer.Option(..., "--run", help="Run ID to mark as milestone"),
    comment: Optional[str] = typer.Option(None, "--comment", help="Milestone comment"),
) -> None:
    """Mark run as milestone."""
    typer.echo(f"Marking run '{run_id}' as milestone")
    typer.echo("Implementation pending - see Epic 6")
