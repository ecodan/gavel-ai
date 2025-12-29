"""OneShot evaluation workflow CLI commands."""
from pathlib import Path
from typing import Optional

import typer

from gavel_ai.cli.scaffolding import generate_all_templates
from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)

app = typer.Typer(
    name="oneshot",
    help="OneShot evaluation workflow commands",
    add_completion=False,
)

DEFAULT_EVAL_ROOT = ".gavel/evaluations"


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
        with tracer.start_as_current_span("cli.oneshot.create") as span:
            span.set_attribute("eval_name", eval)
            span.set_attribute("eval_type", type)

            # Validate evaluation name
            if not eval.replace("-", "").replace("_", "").isalnum():
                raise ValidationError(
                    f"Invalid evaluation name '{eval}' - "
                    "Use only alphanumeric characters, hyphens, and underscores"
                )

            # Determine eval root directory
            eval_root_path: Path = (
                Path(eval_root) if eval_root else Path(DEFAULT_EVAL_ROOT)
            )
            eval_path = eval_root_path / eval

            # Check if evaluation already exists
            if eval_path.exists():
                raise ConfigError(
                    f"Evaluation '{eval}' already exists - "
                    "Use different name or delete existing evaluation"
                )

            # Generate all templates
            generate_all_templates(eval_root_path, eval, type)

            typer.echo(f"✅ Created evaluation '{eval}' at {eval_path}")
            typer.echo(f"   Type: {type}")
            typer.echo(f"   Location: {eval_path.absolute()}")
            typer.echo("\nNext steps:")
            typer.echo(f"  1. Edit config files in {eval_path / 'config'}")
            typer.echo(f"  2. Add scenarios to {eval_path / 'data'}")
            typer.echo(f"  3. Run: gavel oneshot run --eval {eval}")
    except (ConfigError, ValidationError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command()
def run(
    eval: str = typer.Option(..., "--eval", help="Evaluation name"),
    scenarios: Optional[str] = typer.Option(None, "--scenarios", help="Scenario filter (e.g., 1-10)"),
) -> None:
    """Run evaluation scenarios."""
    with tracer.start_as_current_span("cli.oneshot.run"):
        typer.echo(f"Running evaluation '{eval}'")
        typer.echo("Implementation pending - see Epic 3")


@app.command()
def judge(
    run_id: str = typer.Option(..., "--run", help="Run ID to judge"),
    judges: Optional[str] = typer.Option(None, "--judges", help="Comma-separated judge names"),
) -> None:
    """Judge evaluation results."""
    with tracer.start_as_current_span("cli.oneshot.judge"):
        typer.echo(f"Judging run '{run_id}'")
        typer.echo("Implementation pending - see Epic 4")


@app.command()
def report(
    run_id: str = typer.Option(..., "--run", help="Run ID to report"),
    template: Optional[str] = typer.Option(None, "--template", help="Custom report template"),
) -> None:
    """Generate evaluation report."""
    with tracer.start_as_current_span("cli.oneshot.report"):
        typer.echo(f"Generating report for run '{run_id}'")
        typer.echo("Implementation pending - see Epic 5")


@app.command()
def list(
    eval: Optional[str] = typer.Option(None, "--eval", help="Evaluation name to filter"),
) -> None:
    """List evaluation runs."""
    with tracer.start_as_current_span("cli.oneshot.list"):
        typer.echo("Listing evaluation runs")
        typer.echo("Implementation pending - see Epic 6")


@app.command()
def milestone(
    run_id: str = typer.Option(..., "--run", help="Run ID to mark as milestone"),
    comment: Optional[str] = typer.Option(None, "--comment", help="Milestone comment"),
) -> None:
    """Mark run as milestone."""
    with tracer.start_as_current_span("cli.oneshot.milestone"):
        typer.echo(f"Marking run '{run_id}' as milestone")
        typer.echo("Implementation pending - see Epic 6")
