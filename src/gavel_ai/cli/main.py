"""Main Typer CLI application for Gavel-AI."""
from typing import Optional

import typer

from gavel_ai.cli.workflows import autotune, conv, oneshot
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)

# Create main Typer app
app = typer.Typer(
    name="gavel",
    help="Open-source, provider-agnostic AI evaluation framework",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo("gavel-ai version 0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Gavel-AI: Open-source, provider-agnostic AI evaluation framework."""
    pass


# Register workflow subcommands
app.add_typer(oneshot.app, name="oneshot", help="OneShot evaluation workflow commands")
app.add_typer(conv.app, name="conv", help="Conversational evaluation workflow commands (v2+)")
app.add_typer(
    autotune.app, name="autotune", help="Autotune evaluation workflow commands (v3+)"
)


if __name__ == "__main__":
    app()
