"""Conversational evaluation workflow CLI commands (v2+)."""

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.core.steps.generate_step import GenerateStep
from gavel_ai.log_config import get_application_logger
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)
app_logger = get_application_logger()

DEFAULT_EVAL_ROOT = Path(".gavel/evaluations")

app = typer.Typer(
    name="conv",
    help="Conversational evaluation workflow commands (v2+)",
    add_completion=False,
)


@app.command()
def create(
    eval_name: Annotated[str, typer.Option("--eval", help="Evaluation name")],
) -> None:
    """Create conversational evaluation scaffold."""
    typer.echo(f"Creating conversational evaluation scaffold for '{eval_name}'...")
    # Scaffolding implementation will be fully implemented in Task 2
    typer.echo("Scaffolding implementation pending")


@app.command()
def generate(
    eval_name: Annotated[str, typer.Option("--eval", help="Evaluation name")],
    prompt_file: Annotated[
        Optional[Path],
        typer.Option(
            "--prompt-file", help="Custom prompt file (default: prompts/generate_scenarios.toml)"
        ),
    ] = None,
) -> None:
    """Generate scenarios using LLM."""
    app_logger.info(f"Conversational Scenario Generation for '{eval_name}' started")

    try:
        # Create evaluation context
        eval_ctx = LocalFileSystemEvalContext(eval_name=eval_name, eval_root=DEFAULT_EVAL_ROOT)

        # Create run context for the generation process
        run_ctx = LocalRunContext(eval_ctx)

        # If custom prompt file provided, override in eval_config temporarily
        if prompt_file:
            config = eval_ctx.eval_config.read()
            if not hasattr(config, "scenario_generation"):
                # Handle dictionary if it's not a model
                if isinstance(config, dict):
                    if "scenario_generation" not in config:
                        config["scenario_generation"] = {}
                    config["scenario_generation"]["prompt_file"] = str(prompt_file.absolute())
                else:
                    # It's an EvalConfig model
                    config.scenario_generation = {"prompt_file": str(prompt_file.absolute())}
            else:
                config.scenario_generation["prompt_file"] = str(prompt_file.absolute())

            eval_ctx.eval_config.write(config)

        # Execute the generation step
        step = GenerateStep(app_logger)
        asyncio.run(step.execute(run_ctx))

        typer.echo(f"✅ Generated scenarios for '{eval_name}'")
        typer.echo(f"   Run ID: {run_ctx.run_id}")

    except (ConfigError, ValidationError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED, err=True)
        app_logger.error(f"Scenario generation failed: {e}", exc_info=True)
        raise typer.Exit(code=1) from None
