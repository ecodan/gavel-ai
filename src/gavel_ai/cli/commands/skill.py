"""Skill management CLI commands."""

import shutil
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Optional

import typer

app = typer.Typer(
    name="skill",
    help="Manage the gavel Claude Code skill",
    add_completion=False,
)

_SKILL_NAME = "gavel-skill"
_DEFAULT_DEST = ".agent/skills"


@app.command()
def install(
    path: Annotated[
        Optional[str],
        typer.Option("--path", help=f"Destination directory (default: {_DEFAULT_DEST})"),
    ] = None,
    force: bool = typer.Option(False, "--force", help="Overwrite existing skill"),
) -> None:
    """Install the gavel Claude Code skill into this project."""
    dest: Path = Path(path or _DEFAULT_DEST) / _SKILL_NAME

    if dest.exists() and not force:
        typer.secho(
            f"Skill already installed at {dest}. Use --force to overwrite.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(code=0)

    skill_pkg = files("gavel_ai") / "skill" / _SKILL_NAME
    _copy_skill(skill_pkg, dest)

    typer.secho(f"Skill installed at {dest}", fg=typer.colors.GREEN)
    typer.echo(f"Add it to Claude Code by pointing your skill config at {dest}/SKILL.md")


_INSTALL_ITEMS = ("SKILL.md", "references", "scripts")


def _copy_skill(src: object, dest: Path) -> None:
    """Copy only the installable skill items (SKILL.md, references/, scripts/) to dest."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for name in _INSTALL_ITEMS:
        item = src / name  # type: ignore[operator]
        _copy_traversable(item, dest / name)


def _copy_traversable(src: object, dest: Path) -> None:
    if src.is_dir():  # type: ignore[union-attr]
        dest.mkdir(parents=True, exist_ok=True)
        for child in src.iterdir():  # type: ignore[union-attr]
            _copy_traversable(child, dest / child.name)
    else:
        dest.write_bytes(src.read_bytes())  # type: ignore[union-attr]
