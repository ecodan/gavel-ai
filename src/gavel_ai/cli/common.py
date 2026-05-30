"""Common CLI utilities and error handling."""

import asyncio
import json
from pathlib import Path
from typing import Any, Coroutine, NoReturn, Optional, TypeVar

import typer

from gavel_ai.core.exceptions import GavelError
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)

_T = TypeVar("_T")

_DEFAULT_EVAL_ROOT: str = ".gavel/evaluations"
_PROJECT_CONFIG_PATH: Path = Path(".gavel") / "config.json"


def _suppress_task_destroy_warnings(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """Suppress harmless 'Task was destroyed but it is pending' from aiohttp/google-genai cleanup."""
    if "Task was destroyed but it is pending" in context.get("message", ""):
        return
    loop.default_exception_handler(context)


def run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """
    Run an async coroutine to completion with proper cleanup.

    Replaces bare ``asyncio.run()`` calls to suppress spurious
    "Task was destroyed but it is pending!" warnings that aiohttp and
    google-genai emit when their internal async HTTP-client cleanup tasks
    are garbage-collected after the event loop closes.
    """
    loop = asyncio.new_event_loop()
    loop.set_exception_handler(_suppress_task_destroy_warnings)
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            asyncio.set_event_loop(None)
            loop.close()


def handle_error(error: Exception) -> NoReturn:
    """Handle CLI errors with helpful messages.

    Error message format: <ErrorType>: <What happened> - <Recovery step>
    """
    if isinstance(error, GavelError):
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
    else:
        typer.secho(f"Unexpected error: {error}", fg=typer.colors.RED, err=True)

    raise typer.Exit(code=1)


def read_project_config() -> dict:
    """Read .gavel/config.json from the current working directory.

    Returns {} if the file is absent or unparseable.
    """
    try:
        if _PROJECT_CONFIG_PATH.exists():
            return json.loads(_PROJECT_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def resolve_eval_root(eval_root_str: Optional[str]) -> Path:
    """Resolve the evaluation root directory.

    Resolution order (highest to lowest priority):
      1. eval_root_str — from --eval-root CLI flag or GAVEL_EVAL_ROOT env var
         (Typer resolves envvar= into the argument before this function is called)
      2. eval_root field in .gavel/config.json (written by `gavel init`)
      3. Built-in default: .gavel/evaluations
    """
    if eval_root_str is not None:
        return Path(eval_root_str)
    config_root: Optional[str] = read_project_config().get("eval_root")
    if config_root:
        return Path(config_root)
    return Path(_DEFAULT_EVAL_ROOT)
