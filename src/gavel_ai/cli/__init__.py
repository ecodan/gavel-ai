"""
Cli module for gavel-ai.

CLI command interface and Typer application factory.

This module provides the command-line interface for gavel-ai, with hierarchical commands
for different evaluation workflows (OneShot, Conversational, Autotune).

"""
from gavel_ai.cli.main import app

# Export public API
__all__ = ["app"]
