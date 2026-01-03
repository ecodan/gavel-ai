"""OneShot evaluation workflow CLI commands."""
import json
import shutil
from pathlib import Path
from typing import Optional

import typer

from gavel_ai.cli.scaffolding import generate_all_templates
from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.log_config import get_application_logger
from gavel_ai.telemetry import configure_run_telemetry, get_metadata_collector, get_tracer, reset_telemetry, reset_metadata_collector

tracer = get_tracer(__name__)
app_logger = get_application_logger()

app = typer.Typer(
    name="oneshot",
    help="OneShot evaluation workflow commands",
    add_completion=False,
)

DEFAULT_EVAL_ROOT = ".gavel/evaluations"


@app.command()
def create(
    eval: str = typer.Option(..., "--eval", help="Evaluation name"),
    type: str = typer.Option("local", "--type", help="Evaluation type: local or in-situ"),
    eval_root: Optional[str] = typer.Option(
        None, "--eval-root", help="Custom evaluation root directory"
    ),
) -> None:
    """Create a new evaluation scaffold."""
    try:
        with tracer.start_as_current_span("cli.oneshot.create") as span:
            span.set_attribute("eval_name", eval)
            span.set_attribute("eval_type", type)

            # Validate evaluation name
            if not eval.replace("-", "").replace("_", "").isalnum():
                raise ValidationError(
                    f"Invalid evaluation name '{eval}' - "
                    "Use only alphanumeric characters, hyphens, and underscores"
                )

            # Determine eval root directory
            eval_root_path: Path = (
                Path(eval_root) if eval_root else Path(DEFAULT_EVAL_ROOT)
            )
            eval_path = eval_root_path / eval

            # Check if evaluation already exists
            if eval_path.exists():
                raise ConfigError(
                    f"Evaluation '{eval}' already exists - "
                    "Use different name or delete existing evaluation"
                )

            # Generate all templates
            generate_all_templates(eval_root_path, eval, type)

            app_logger.info(f"Evaluation '{eval}' created at {eval_path}")

            typer.echo(f"✅ Created evaluation '{eval}' at {eval_path}")
            typer.echo(f"   Type: {type}")
            typer.echo(f"   Location: {eval_path.absolute()}")
            typer.echo("\nNext steps:")
            typer.echo(f"  1. Edit config files in {eval_path / 'config'}")
            typer.echo(f"  2. Add scenarios to {eval_path / 'data'}")
            typer.echo(f"  3. Run: gavel oneshot run --eval {eval}")
    except (ConfigError, ValidationError) as e:
        app_logger.error(f"Failed to create evaluation '{eval}': {e}", exc_info=True)
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command()
def run(
    eval: str = typer.Option(..., "--eval", help="Evaluation name"),
    scenarios: Optional[str] = typer.Option(None, "--scenarios", help="Scenario filter (e.g., 1-10)"),
) -> None:
    """Run evaluation scenarios."""
    import asyncio
    import time
    from datetime import datetime, timezone

    from gavel_ai.core.config.agents import ModelDefinition
    from gavel_ai.core.config_loader import ConfigLoader
    from gavel_ai.core.executor import Executor
    from gavel_ai.core.models import Input, ProcessorConfig, ReporterConfig
    from gavel_ai.core.result_storage import ResultStorage
    from gavel_ai.judges.judge_executor import JudgeExecutor
    from gavel_ai.log_config import get_run_logger
    from gavel_ai.processors.closedbox_processor import ClosedBoxInputProcessor
    from gavel_ai.processors.prompt_processor import PromptInputProcessor
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter
    from gavel_ai.storage.filesystem import LocalFilesystemRun

    start_time = time.time()
    app_logger.info(f"Evaluation '{eval}' started")

    # Create run_id early for run-level logging and telemetry
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    run_logger = get_run_logger(run_id=run_id, eval_name=eval)

    # Configure telemetry export for this run
    telemetry_path = configure_run_telemetry(run_id=run_id, eval_name=eval, base_dir=".gavel")
    run_logger.info(f"Telemetry export configured: {telemetry_path}")

    # Initialize metadata collector and record run start
    metadata_collector = get_metadata_collector()
    metadata_collector.record_run_start()
    run_logger.info("Metadata collector initialized and run start recorded")

    try:
        with tracer.start_as_current_span("cli.oneshot.run") as span:
            # 1. Load configs
            typer.echo(f"Running evaluation '{eval}'")
            run_logger.info(f"Loading configuration for evaluation '{eval}'")

            loader = ConfigLoader(Path(DEFAULT_EVAL_ROOT), eval)

            run_logger.info("Loading eval_config.json")
            eval_config = loader.load_eval_config()

            # Async config is now nested in eval_config
            async_config = eval_config.async_config

            run_logger.info("Loading agents.json")
            agents_config = loader.load_agents_config()

            run_logger.info("Loading scenarios")
            scenarios_list = loader.load_scenarios()
            run_logger.info(f"Loaded {len(scenarios_list)} scenarios")

            typer.echo(f"✓ Loaded {len(scenarios_list)} scenarios")

            # 2. Create run context
            run_metadata = {
                "eval_name": eval,
                "run_id": run_id,
                "start_time": datetime.now(timezone.utc).isoformat(),
            }

            run_obj = LocalFilesystemRun(
                run_id=run_id,
                eval_name=eval,
                metadata=run_metadata,
                base_dir=".gavel",
            )

            typer.echo(f"✓ Created run: {run_id}")
            span.set_attribute("run_id", run_id)

            # 2.5. Copy evaluation configs to run/config/ for reproducibility
            source_config_dir = Path(DEFAULT_EVAL_ROOT) / eval / "config"
            dest_config_dir = run_obj.run_dir / "config"
            if source_config_dir.exists():
                run_logger.info(f"Copying config directory to {dest_config_dir}")
                shutil.copytree(source_config_dir, dest_config_dir, dirs_exist_ok=True)
                typer.echo(f"✓ Copied evaluation configs to run directory")
            else:
                run_logger.warning(f"Config directory not found at {source_config_dir}")

            # 3. Instantiate processor
            # Get model definition from agents config
            models = agents_config.get("_models", {})
            subject_agent = agents_config.get("subject_agent", {})
            model_id = subject_agent.get("model_id")

            if not model_id or model_id not in models:
                raise ConfigError(
                    f"Subject agent model_id '{model_id}' not found in _models - "
                    f"Check agents.json configuration"
                )

            model_data = models[model_id]
            model_def = ModelDefinition.model_validate(model_data)

            # Extract test subject (prompt/system under test) and model variant
            test_subject = subject_agent.get("prompt", "unknown")
            model_variant = model_data.get("model_version", "unknown")

            # Determine processor type based on test_subject_type
            processor_type = "prompt_input" if eval_config.test_subject_type == "local" else "closedbox_input"

            # Create processor config
            processor_config = ProcessorConfig(
                processor_type=processor_type,
                parallelism=async_config.num_workers,
                timeout_seconds=async_config.task_timeout_seconds,
                error_handling="fail_fast",  # Default error handling
            )

            if processor_type == "prompt_input":
                processor = PromptInputProcessor(
                    config=processor_config,
                    model_def=model_def,
                )
            elif processor_type == "closedbox_input":
                processor = ClosedBoxInputProcessor(
                    config=processor_config,
                    model_def=model_def,
                )
            else:
                raise ConfigError(
                    f"Unknown processor_type '{processor_type}' - "
                    f"Use 'prompt_input' or 'closedbox_input'"
                )

            typer.echo(f"✓ Initialized {processor_type} processor")
            run_logger.info(f"Initialized {processor_type} processor")

            # 4. Convert scenarios to inputs
            inputs = [
                Input(
                    id=scenario.scenario_id,
                    text=scenario.input,  # input is now a string
                    metadata=scenario.metadata or {},
                )
                for scenario in scenarios_list
            ]

            # 5. Execute scenarios
            typer.echo(f"Executing {len(inputs)} scenarios...")
            run_logger.info(f"Executing {len(inputs)} scenarios with {async_config.num_workers} workers")

            executor = Executor(
                processor=processor,
                parallelism=async_config.num_workers,
                error_handling="fail_fast",  # Use default error handling
            )

            processor_results = asyncio.run(executor.execute(inputs))
            run_logger.info(f"Completed execution of {len(processor_results)} scenarios")
            typer.echo(f"✓ Executed {len(processor_results)} scenarios")

            # 6. Execute judges (if configured)
            # Judges are now part of test_subjects
            judges_list = []
            if eval_config.test_subjects:
                for subject in eval_config.test_subjects:
                    if subject.judges:
                        judges_list.extend(subject.judges)

            if judges_list:
                typer.echo(f"Running {len(judges_list)} judges...")
                run_logger.info(
                    f"Running {len(judges_list)} judges on {len(processor_results)} results"
                )

                judge_executor = JudgeExecutor(
                    judge_configs=judges_list,
                    error_handling="fail_fast",  # Use default error handling
                )

                # Execute judges on each result
                evaluation_results = []
                for scenario, proc_result in zip(scenarios_list, processor_results, strict=True):
                    eval_result = asyncio.run(
                        judge_executor.execute(
                            scenario=scenario,
                            subject_output=str(proc_result.output),
                            variant_id="subject_agent",
                            subject_id="PUT",
                        )
                    )
                    evaluation_results.append(eval_result)

                run_logger.info(f"Completed judging {len(evaluation_results)} results")
                typer.echo("✓ Completed judging")
            else:
                evaluation_results = []
                run_logger.info("No judges configured - skipping judging")
                typer.echo("⚠ No judges configured - skipping judging")

            # 7. Store results (two-file design: results_raw.jsonl and results_judged.jsonl)
            from gavel_ai.storage.results_exporter import ResultsExporter

            exporter = ResultsExporter(run_obj.run_dir, processor_type=eval_config.processor_type)

            # Export raw processor results (immutable)
            run_logger.info(f"Exporting {len(processor_results)} processor results to results_raw.jsonl")
            raw_results_file = exporter.export_raw_results(
                scenarios_list,
                processor_results,
                test_subject=test_subject,
                variant_id=model_variant,
            )
            typer.echo(f"✓ Exported raw results to {raw_results_file.name}")

            # Export judged results (mutable)
            run_logger.info(f"Exporting {len(processor_results)} judged results to results_judged.jsonl")
            judged_results_file = exporter.export_judged_results(
                scenarios=scenarios_list,
                processor_results=processor_results,
                judge_evaluations=[r.model_dump() if hasattr(r, 'model_dump') else r for r in evaluation_results],
                test_subject=test_subject,
                variant_id=model_variant,
            )
            typer.echo(f"✓ Exported judged results to {judged_results_file.name}")

            # 7.5. Generate manifest.json with reproducibility info
            manifest_file = run_obj.run_dir / "manifest.json"
            try:
                # Compute config hash for reproducibility
                config_files_for_hash = {
                    "agents": run_obj.run_dir / "config" / "agents.json",
                    "eval_config": run_obj.run_dir / "config" / "eval_config.json",
                    "async_config": run_obj.run_dir / "config" / "async_config.json",
                }
                # Scenarios might be in config or might be in data - try both
                scenarios_path = run_obj.run_dir / "config" / "scenarios.json"
                if scenarios_path.exists():
                    config_files_for_hash["scenarios"] = scenarios_path
                else:
                    # Try scenarios.csv in the original evaluation data directory
                    alt_scenarios = Path(DEFAULT_EVAL_ROOT) / eval / "data" / "scenarios.json"
                    if alt_scenarios.exists():
                        config_files_for_hash["scenarios"] = alt_scenarios
                    else:
                        run_logger.warning("Could not find scenarios file for config hash")

                config_hash = exporter.compute_config_hash(config_files_for_hash) if len(config_files_for_hash) >= 3 else "unknown"

                # Determine status based on results
                failed_count = sum(1 for pr in processor_results if pr.error is not None)
                status = "completed" if failed_count == 0 else "partial" if failed_count < len(processor_results) else "failed"

                manifest_data = {
                    "timestamp": run_metadata["start_time"],
                    "run_id": run_id,
                    "eval_name": eval,
                    "config_hash": config_hash,
                    "scenario_count": len(scenarios_list),
                    "variant_count": 1,  # Currently fixed at 1 (subject_agent)
                    "judge_count": len(eval_config.judges) if eval_config.judges else 0,
                    "processor_type": eval_config.processor_type,
                    "status": status,
                    "completed_count": len(scenarios_list) - failed_count,
                    "failed_count": failed_count,
                    "duration_seconds": time.time() - start_time,
                }

                with open(manifest_file, "w", encoding="utf-8") as f:
                    json.dump(manifest_data, f, indent=2)
                run_logger.info(f"Manifest saved to {manifest_file}")
                typer.echo(f"✓ Generated manifest with config hash")
            except FileNotFoundError as e:
                run_logger.warning(f"Could not compute config hash: {e}")

            # 8. Record run end and compute metadata (BEFORE report generation)
            run_logger.info("Recording run end and computing metadata statistics")
            metadata_collector.record_run_end()
            run_metadata_stats = metadata_collector.compute_statistics(
                run_id=run_id,
                eval_name=eval,
            )
            run_logger.info(f"Metadata computed - {run_metadata_stats.scenario_timing.count} scenarios processed")

            # Save metadata to file
            metadata_file = run_obj.run_dir / "run_metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                f.write(run_metadata_stats.model_dump_json(indent=2))
            run_logger.info(f"Run metadata saved to {metadata_file}")
            typer.echo(f"✓ Saved run metadata to {metadata_file}")

            # 9. Generate report (AFTER metadata is computed and saved)
            report_path = run_obj.run_dir / "report.html"
            # Use absolute path to templates directory
            from gavel_ai.reporters.jinja_reporter import Jinja2Reporter
            templates_dir = Path(__file__).parent.parent.parent / "reporters" / "templates"
            reporter_config = ReporterConfig(
                template_path=str(templates_dir),
                output_format="html",
            )
            reporter = OneShotReporter(reporter_config)

            # Set run data for reporter
            run_obj.results_data = (
                [r.model_dump() for r in evaluation_results] if evaluation_results else []
            )
            run_obj.metadata_data = run_metadata
            # Also set results and telemetry attributes for the reporter to access
            run_obj.results = run_obj.results_data
            # Set telemetry from run_metadata_stats for template rendering
            run_obj.telemetry = {
                "total_duration_seconds": run_metadata_stats.total_duration_seconds,
                "llm_calls": run_metadata_stats.llm_calls.model_dump(),
            }

            run_logger.info(f"Generating report to {report_path}")
            report_content = asyncio.run(reporter.generate(run_obj, "oneshot.html"))
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            run_logger.info(f"Successfully generated report: {report_path}")
            typer.echo(f"✓ Generated report: {report_path}")

            # 10. Save run
            run_logger.info("Saving run manifest")
            asyncio.run(run_obj.save())
            run_logger.info("Run saved successfully")

            # Calculate duration
            duration = time.time() - start_time
            app_logger.info(f"Evaluation '{eval}' completed in {duration:.2f}s")

            # 11. Print summary
            typer.echo("\n✅ Evaluation complete")
            typer.echo(f"   Run ID: {run_id}")
            typer.echo(f"   Scenarios: {len(scenarios_list)}")
            if eval_config.judges:
                typer.echo(f"   Judges: {len(eval_config.judges)}")
            typer.echo(f"   Report: {report_path.absolute()}")
            typer.echo(f"   Telemetry: {telemetry_path.absolute()}")

    except ConfigError as e:
        run_logger.error(f"Configuration error: {e}", exc_info=True)
        app_logger.error(f"Configuration error in evaluation '{eval}': {e}", exc_info=True)
        typer.secho(f"Configuration Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except ValidationError as e:
        run_logger.error(f"Validation error: {e}", exc_info=True)
        app_logger.error(f"Validation error in evaluation '{eval}': {e}", exc_info=True)
        typer.secho(f"Validation Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        run_logger.error(f"Execution error: {e}", exc_info=True)
        app_logger.error(f"Execution error in evaluation '{eval}': {e}", exc_info=True)
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    finally:
        # Always reset telemetry and metadata after run completes (success or failure)
        reset_telemetry()
        reset_metadata_collector()
        run_logger.info("Telemetry and metadata collector reset after run completion")


@app.command()
def judge(
    run_id: str = typer.Option(..., "--run", help="Run ID to judge"),
    judges: Optional[str] = typer.Option(None, "--judges", help="Comma-separated judge names"),
) -> None:
    """Judge evaluation results."""
    with tracer.start_as_current_span("cli.oneshot.judge"):
        typer.echo(f"Judging run '{run_id}'")
        typer.echo("Implementation pending - see Epic 4")


@app.command()
def report(
    run_id: str = typer.Option(..., "--run", help="Run ID to report"),
    template: Optional[str] = typer.Option(None, "--template", help="Custom report template"),
) -> None:
    """Generate evaluation report."""
    with tracer.start_as_current_span("cli.oneshot.report"):
        typer.echo(f"Generating report for run '{run_id}'")
        typer.echo("Implementation pending - see Epic 5")


@app.command()
def list(
    eval: Optional[str] = typer.Option(None, "--eval", help="Evaluation name to filter"),
) -> None:
    """List evaluation runs."""
    with tracer.start_as_current_span("cli.oneshot.list"):
        typer.echo("Listing evaluation runs")
        typer.echo("Implementation pending - see Epic 6")


@app.command()
def milestone(
    run_id: str = typer.Option(..., "--run", help="Run ID to mark as milestone"),
    comment: Optional[str] = typer.Option(None, "--comment", help="Milestone comment"),
) -> None:
    """Mark run as milestone."""
    with tracer.start_as_current_span("cli.oneshot.milestone"):
        typer.echo(f"Marking run '{run_id}' as milestone")
        typer.echo("Implementation pending - see Epic 6")
