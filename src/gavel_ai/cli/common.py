"""Common CLI utilities and error handling."""
from typing import NoReturn

import typer

from gavel_ai.core.exceptions import GavelError
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)


def handle_error(error: Exception) -> NoReturn:
    """Handle CLI errors with helpful messages.

    Error message format: <ErrorType>: <What happened> - <Recovery step>
    """
    if isinstance(error, GavelError):
        # GavelError already has formatted message
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
    else:
        # Generic error
        typer.secho(f"Unexpected error: {error}", fg=typer.colors.RED, err=True)

    raise typer.Exit(code=1)
