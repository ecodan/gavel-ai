"""OneShot evaluation workflow CLI commands."""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table

from gavel_ai.cli.scaffolding import generate_all_templates
from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.exceptions import ConfigError, ResourceNotFoundError, ValidationError
from gavel_ai.core.workflows.oneshot import OneShotWorkflow
from gavel_ai.judges.rejudge import ReJudge
from gavel_ai.log_config import get_application_logger
from gavel_ai.models.runtime import ReporterConfig
from gavel_ai.reporters.oneshot_reporter import OneShotReporter
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)
app_logger = get_application_logger()

DEFAULT_EVAL_ROOT = Path(".gavel/evaluations")

app = typer.Typer(
    name="oneshot",
    help="OneShot evaluation workflow commands",
    add_completion=False,
)
console = Console()

def _get_eval_dir(eval_name: Optional[str], run_id: Optional[str] = None) -> tuple[str, Path]:
    """Discover evaluation directory given eval name or run_id."""
    if eval_name:
        eval_path = DEFAULT_EVAL_ROOT / eval_name
        if not eval_path.exists():
            raise ResourceNotFoundError(f"Evaluation '{eval_name}' not found")
        return eval_name, eval_path

    if not run_id:
        raise ConfigError("Must provide either --eval or --run")

    if not DEFAULT_EVAL_ROOT.exists():
        raise ConfigError("No evaluations found. Use 'gavel oneshot create' first.")
    
    for eval_dir in DEFAULT_EVAL_ROOT.iterdir():
        if eval_dir.is_dir() and (eval_dir / "runs" / run_id).exists():
            return eval_dir.name, eval_dir
    
    raise ResourceNotFoundError(f"Run ID '{run_id}' not found in any evaluation")

def _print_run_summary(run_ctx: LocalRunContext, eval_ctx: LocalFileSystemEvalContext) -> None:
    eval_config = eval_ctx.eval_config.read()
    scenarios = eval_ctx.scenarios.read()
    
    judge_count = sum(
        len(subject.judges) for subject in (eval_config.test_subjects or []) if subject.judges
    )

    console.print("\n[bold green]✅ Evaluation complete[/bold green]")
    console.print(f"   Run ID: [cyan]{run_ctx.run_id}[/cyan]")
    console.print(f"   Scenarios: [cyan]{len(scenarios)}[/cyan]")
    if judge_count > 0:
        console.print(f"   Judges: [cyan]{judge_count}[/cyan]")
    console.print(f"   Report: {run_ctx.run_dir / 'report.html'}")



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
        # Validate evaluation name
        if not eval.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                f"Invalid evaluation name '{eval}' - "
                "Use only alphanumeric characters, hyphens, and underscores"
            )

        # Determine eval root directory
        eval_root_path: Path = Path(eval_root) if eval_root else Path(DEFAULT_EVAL_ROOT)
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
    eval_name: str = typer.Option(..., "--eval", help="Evaluation name"),
    scenarios: Optional[str] = typer.Option(
        None, "--scenarios", help="Scenario filter (e.g., 1-10)"
    ),
) -> None:
    """CLI entry point for OneShot evaluation workflow."""
    app_logger.info(f"OneShot Evaluation '{eval_name}' started")

    # Create evaluation context
    eval_ctx = LocalFileSystemEvalContext(eval_name=eval_name, eval_root=DEFAULT_EVAL_ROOT)

    try:
        # Call business logic (core tier) - run async workflow
        workflow = OneShotWorkflow(eval_ctx, app_logger)
        run_ctx = asyncio.run(workflow.execute())

        # Format output for CLI (presentation tier)
        typer.echo(f"✓ Created run: {run_ctx.run_id}")
        typer.echo("✓ Completed validation")
        typer.echo("✓ Completed scenario_processing")
        typer.echo("✓ Completed judging")
        typer.echo("✓ Completed reporting")

        # Print summary
        _print_run_summary(run_ctx, eval_ctx)

    except (ConfigError, ValidationError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command()
def judge(
    run_id: str = typer.Option(..., "--run", help="Run ID to judge"),
    eval_name: Optional[str] = typer.Option(None, "--eval", help="Evaluation name"),
    judges: Optional[str] = typer.Option(None, "--judges", help="Comma-separated judge names"),
) -> None:
    """Judge evaluation results."""
    try:
        real_eval_name, eval_dir = _get_eval_dir(eval_name, run_id)
        eval_ctx = LocalFileSystemEvalContext(eval_name=real_eval_name, eval_root=DEFAULT_EVAL_ROOT)
        run_ctx = LocalRunContext(
            eval_ctx=eval_ctx, 
            base_dir=eval_dir / "runs",
            run_id=run_id,
            snapshot=False
        )
        
        if not run_ctx.results_raw.exists():
            raise ResourceNotFoundError(f"Error: No results found for run '{run_id}'. Did it finish processing?")
            
        console.print(f"Loading processor outputs from run '{run_id}'")
        
        # Determine judges
        eval_config = eval_ctx.eval_config.read()
        judge_configs = []
        if eval_config.test_subjects:
            for subject in eval_config.test_subjects:
                if subject.judges:
                    for j in subject.judges:
                        # Add filtering if --judges was used
                        if not judges or j.id in [x.strip() for x in judges.split(",")]:
                            if j not in judge_configs:
                                judge_configs.append(j)
                                
        if not judge_configs:
            console.print("[yellow]No judges defined for this evaluation or filter matched no judges.[/yellow]")
            return
            
        results_file = run_ctx.run_dir / "results_raw.jsonl"

        rejudge_engine = ReJudge(results_file, judge_configs)

        # Async run
        rejudged = asyncio.run(rejudge_engine.rejudge_all(
            preserve_existing=True,
            output_file=run_ctx.run_dir / "results_judged.jsonl"
        ))
        
        console.print(f"[bold green]✓ Completed judging ({len(judge_configs)} judges applied to {len(rejudged)} outputs)[/bold green]")
        
        # Automatically generate report
        console.print("Generating updated report...")
        _generate_report(run_id, real_eval_name, None)
        
    except (ConfigError, ResourceNotFoundError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


def _generate_report(run_id: str, eval_name: Optional[str], template: Optional[str]) -> None:
    # 1. Discover evaluation if not provided
    real_eval_name, eval_dir = _get_eval_dir(eval_name, run_id)

    # 2. Create contexts
    eval_ctx = LocalFileSystemEvalContext(eval_name=real_eval_name, eval_root=DEFAULT_EVAL_ROOT)
    run_ctx = LocalRunContext(
        eval_ctx=eval_ctx, 
        base_dir=eval_dir / "runs",
        run_id=run_id,
        snapshot=False
    )

    if not (run_ctx.run_dir).exists():
        raise ResourceNotFoundError(f"Run directory not found: {run_ctx.run_dir}")

    typer.echo(f"Generating report for run '{run_id}' in evaluation '{real_eval_name}'...")

    # 3. Load results
    results = []
    if run_ctx.results_judged.exists():
        results = list(run_ctx.results_judged.read())
    elif run_ctx.results_raw.exists():
        results = list(run_ctx.results_raw.read())
    else:
        raise ConfigError(f"No results found for run {run_id}")

    # 4. Load metadata
    metadata = {}
    if run_ctx.run_metadata.exists():
        metadata_obj = run_ctx.run_metadata.read()
        if hasattr(metadata_obj, "model_dump"):
            metadata = metadata_obj.model_dump()
        else:
            metadata = metadata_obj
    else:
        metadata = {
            "eval_name": real_eval_name,
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "unknown"
        }

    # 5. Generate report
    templates_dir = Path(__file__).parent.parent.parent / "reporters" / "templates"
    reporter_config = ReporterConfig(
        template_path=str(templates_dir),
        output_format="html",
    )
    reporter = OneShotReporter(reporter_config)

    class ReportData:
        def __init__(self, metadata, results, run_id):
            self.metadata = metadata
            self.results = results
            self.run_id = run_id

    report_data = ReportData(metadata, results, run_id)
    template_name = template if template else "oneshot.html"
    
    report_content = asyncio.run(reporter.generate(report_data, template_name))
    
    report_path = run_ctx.run_dir / "report.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    typer.echo(f"✅ Report generated: {report_path.absolute()}")

@app.command()
def report(
    run_id: str = typer.Option(..., "--run", help="Run ID to report"),
    eval_name: Optional[str] = typer.Option(None, "--eval", help="Evaluation name"),
    template: Optional[str] = typer.Option(None, "--template", help="Custom report template"),
) -> None:
    """Generate evaluation report."""
    try:
        _generate_report(run_id, eval_name, template)
    except ConfigError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command(name="list")
def list_runs(
    eval_name: Optional[str] = typer.Option(None, "--eval", help="Evaluation name to filter"),
) -> None:
    """List evaluation runs."""
    try:
        evals_to_check = []
        if eval_name:
            _, eval_dir = _get_eval_dir(eval_name)
            evals_to_check = [eval_dir]
        else:
            if not DEFAULT_EVAL_ROOT.exists():
                raise ConfigError("No evaluations found. Use 'gavel oneshot create' first.")
            evals_to_check = [d for d in DEFAULT_EVAL_ROOT.iterdir() if d.is_dir()]
            
        table = Table(title="Evaluation Runs")
        table.add_column("Run ID", style="cyan", no_wrap=True)
        table.add_column("Eval", style="magenta", no_wrap=True)
        table.add_column("Timestamp", style="green")
        table.add_column("Scenarios", justify="right")
        table.add_column("Milestone", justify="center", no_wrap=True)

        has_runs = False
        for eval_dir in evals_to_check:
            runs_dir = eval_dir / "runs"
            if not runs_dir.exists():
                continue
                
            for run_dir in sorted(runs_dir.iterdir(), key=lambda d: d.name, reverse=True):
                if not run_dir.is_dir():
                    continue
                has_runs = True
                
                metadata_file = run_dir / "manifest.json"
                timestamp = "Unknown"
                scenarios = "Unknown"
                milestone = ""
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            data = json.load(f)
                        timestamp = data.get("timestamp", "").split(".")[0].replace("T", " ")
                        scenarios = str(data.get("scenario_count", "Unknown"))
                        is_milestone = data.get("is_milestone", False)
                        comment = data.get("milestone_comment", "")
                        if is_milestone:
                            milestone = f"⭐ {comment}" if comment else "⭐"
                    except Exception:
                        pass
                
                table.add_row(run_dir.name, eval_dir.name, timestamp, scenarios, milestone)
                
        if not has_runs:
            if eval_name:
                console.print(f"No runs found for evaluation '{eval_name}'")
            else:
                console.print("No runs found")
        else:
            console.print(table)
            
    except (ConfigError, ResourceNotFoundError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command()
def milestone(
    run_id: str = typer.Option(..., "--run", help="Run ID to mark as milestone"),
    eval_name: Optional[str] = typer.Option(None, "--eval", help="Evaluation name"),
    comment: Optional[str] = typer.Option(None, "--comment", help="Milestone comment"),
    remove: bool = typer.Option(False, "--remove", help="Remove milestone status"),
) -> None:
    """Mark run as milestone."""
    try:
        eval_name, eval_dir = _get_eval_dir(eval_name, run_id)
        run_dir = eval_dir / "runs" / run_id
        metadata_file = run_dir / "manifest.json"
        
        if not metadata_file.exists():
            raise ResourceNotFoundError(f"Manifest not found for run '{run_id}'")
            
        with open(metadata_file, "r") as f:
            data = json.load(f)
            
        if remove:
            data["is_milestone"] = False
            data["milestone_comment"] = None
            data["milestone_timestamp"] = None
            action = "removed from milestones"
        else:
            data["is_milestone"] = True
            data["milestone_comment"] = comment
            data["milestone_timestamp"] = datetime.now(timezone.utc).isoformat()
            action = f"marked as milestone{f' ({comment})' if comment else ''}"
            
        with open(metadata_file, "w") as f:
            json.dump(data, f, indent=2)
            
        console.print(f"[bold green]✅ Run {run_id}[/bold green] {action}")
        
    except (ConfigError, ResourceNotFoundError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
