"""Autotune evaluation workflow CLI commands (v3+)."""

import typer

from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)

app = typer.Typer(
    name="autotune",
    help="Autotune evaluation workflow commands (v3+)",
    add_completion=False,
)


@app.command()
def create() -> None:
    """Create autotune evaluation scaffold."""
    typer.echo("Autotune evaluation workflow (v3+)")
    typer.echo("Implementation pending")


@app.command()
def run() -> None:
    """Run autotune evaluation."""
    typer.echo("Autotune evaluation workflow (v3+)")
    typer.echo("Implementation pending")
