"""Main Typer CLI application for Gavel-AI."""

import json
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from gavel_ai.cli.commands import autotune, conv, oneshot
from gavel_ai.log_config import get_application_logger
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)
app_logger = get_application_logger()

_PROJECT_CONFIG_PATH: Path = Path(".gavel") / "config.json"

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


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Gavel-AI: Open-source, provider-agnostic AI evaluation framework."""
    load_dotenv(verbose=False, override=False)
    if ctx.invoked_subcommand not in ("init", None) and not _PROJECT_CONFIG_PATH.exists():
        typer.secho(
            "Warning: project not initialized. Run `gavel init` to configure this project.",
            fg=typer.colors.YELLOW,
            err=True,
        )


@app.command()
def init(
    eval_root: Optional[str] = typer.Option(
        None, "--eval-root", help="Eval root directory (default: ./evals)"
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
) -> None:
    """Initialize gavel in the current project directory."""
    if _PROJECT_CONFIG_PATH.exists() and not force:
        typer.secho(
            "Already initialized. Use --force to overwrite.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(code=0)

    root: str = eval_root or typer.prompt("Eval root directory", default="./evals")
    _PROJECT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PROJECT_CONFIG_PATH.write_text(json.dumps({"eval_root": root}, indent=2), encoding="utf-8")
    typer.secho(f"Initialized. Eval root: {root}", fg=typer.colors.GREEN)
    typer.echo("Next: gavel oneshot create --eval <name>")


# Register workflow subcommands
app.add_typer(oneshot.app, name="oneshot", help="OneShot evaluation workflow commands")
app.add_typer(conv.app, name="conv", help="Conversational evaluation workflow commands (v2+)")
app.add_typer(autotune.app, name="autotune", help="Autotune evaluation workflow commands (v3+)")


if __name__ == "__main__":
    app()
