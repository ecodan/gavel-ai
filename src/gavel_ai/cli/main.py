"""Main Typer CLI application for Gavel-AI."""

import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import List, Optional

import typer
from dotenv import load_dotenv

from gavel_ai.cli.commands import autotune, conv, oneshot, skill
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
        try:
            pkg_version = version("gavel-ai")
        except PackageNotFoundError:
            pkg_version = "unknown"
        typer.echo(f"gavel-ai version {pkg_version}")
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
    if ctx.invoked_subcommand not in ("init", "skill", None) and not _PROJECT_CONFIG_PATH.exists():
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
    _update_gitignore(root)
    typer.secho(f"Initialized. Eval root: {root}", fg=typer.colors.GREEN)
    typer.echo("Next: gavel oneshot create --eval <name>")
    typer.echo("Tip:  gavel skill install  — adds the Claude Code skill to this project")


def _update_gitignore(eval_root: str) -> None:
    """Append gavel-specific ignore patterns to .gitignore (idempotent)."""
    # Normalise: strip leading ./ so patterns are clean
    root = eval_root.lstrip("./").rstrip("/") or eval_root.rstrip("/")
    patterns: List[str] = [
        f"{root}/*/runs/",
        ".gavel/gavel.log",
    ]

    gitignore = Path(".gitignore")
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""

    new_lines: List[str] = [p for p in patterns if p not in existing]
    if not new_lines:
        return

    block = "\n# gavel\n" + "\n".join(new_lines) + "\n"
    with gitignore.open("a", encoding="utf-8") as fh:
        if existing and not existing.endswith("\n"):
            fh.write("\n")
        fh.write(block)
    typer.echo(f"Updated .gitignore with {len(new_lines)} gavel pattern(s)")


# Register workflow subcommands
app.add_typer(oneshot.app, name="oneshot", help="OneShot evaluation workflow commands")
app.add_typer(conv.app, name="conv", help="Conversational evaluation workflow commands (v2+)")
app.add_typer(autotune.app, name="autotune", help="Autotune evaluation workflow commands")
app.add_typer(skill.app, name="skill", help="Manage the gavel Claude Code skill")


if __name__ == "__main__":
    app()
