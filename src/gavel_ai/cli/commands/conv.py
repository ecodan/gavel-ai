"""Conversational evaluation workflow CLI commands (v2+)."""

import typer

from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)

app = typer.Typer(
    name="conv",
    help="Conversational evaluation workflow commands (v2+)",
    add_completion=False,
)


@app.command()
def create() -> None:
    """Create conversational evaluation scaffold."""
    typer.echo("Conversational evaluation workflow (v2+)")
    typer.echo("Implementation pending")


@app.command()
def run() -> None:
    """Run conversational evaluation."""
    typer.echo("Conversational evaluation workflow (v2+)")
    typer.echo("Implementation pending")
