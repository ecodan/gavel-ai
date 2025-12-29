"""Scaffolding functions for gavel oneshot create command."""
import csv
import json
from pathlib import Path
from typing import Any, Dict

from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)


def generate_agents_config(eval_root: Path, eval_name: str) -> None:
    """Generate agents.json template with sensible defaults."""
    agents_config: Dict[str, Any] = {
        "_models": {
            "claude-standard": {
                "model_provider": "anthropic",
                "model_family": "claude",
                "model_version": "claude-sonnet-4-5-latest",
                "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                "provider_auth": {"api_key": "<YOUR_ANTHROPIC_API_KEY>"},
            },
            "gpt-standard": {
                "model_provider": "openai",
                "model_family": "gpt",
                "model_version": "gpt-4o",
                "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                "provider_auth": {"api_key": "<YOUR_OPENAI_API_KEY>"},
            },
        },
        "subject_agent": {"model_id": "claude-standard", "prompt": "assistant:v1"},
        "baseline_agent": {"model_id": "gpt-standard", "prompt": "assistant:v1"},
    }

    output_file = eval_root / eval_name / "config" / "agents.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(agents_config, f, indent=2)


def generate_eval_config(eval_root: Path, eval_name: str, eval_type: str) -> None:
    """Generate eval_config.json template."""
    eval_config: Dict[str, Any] = {
        "eval_name": eval_name,
        "eval_type": eval_type,
        "processor_type": "prompt_input",
        "scenarios_file": "data/scenarios.json",
        "agents_file": "config/agents.json",
        "judges_config": "config/judges/",
        "output_dir": "runs/",
    }

    output_file = eval_root / eval_name / "config" / "eval_config.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(eval_config, f, indent=2)


def generate_async_config(eval_root: Path, eval_name: str) -> None:
    """Generate async_config.json template."""
    async_config: Dict[str, Any] = {
        "max_workers": 4,
        "timeout_seconds": 30,
        "retry_count": 3,
        "error_handling": "fail_fast",
    }

    output_file = eval_root / eval_name / "config" / "async_config.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(async_config, f, indent=2)


def generate_scenarios_json(eval_root: Path, eval_name: str) -> None:
    """Generate scenarios.json template with sample scenarios."""
    scenarios_data: Dict[str, Any] = {
        "scenarios": [
            {
                "scenario_id": "scenario-1",
                "input": "What is the capital of France?",
                "expected_output": "Paris",
                "metadata": {"category": "geography", "difficulty": "easy"},
            },
            {
                "scenario_id": "scenario-2",
                "input": "Explain quantum computing in simple terms",
                "expected_output": "",
                "metadata": {"category": "technology", "difficulty": "medium"},
            },
        ]
    }

    output_file = eval_root / eval_name / "data" / "scenarios.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(scenarios_data, f, indent=2)


def generate_scenarios_csv(eval_root: Path, eval_name: str) -> None:
    """Generate scenarios.csv template with sample scenarios."""
    output_file = eval_root / eval_name / "data" / "scenarios.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["scenario_id", "input", "expected_output", "category", "difficulty"]
        )
        writer.writerow(
            [
                "scenario-1",
                "What is the capital of France?",
                "Paris",
                "geography",
                "easy",
            ]
        )
        writer.writerow(
            [
                "scenario-2",
                "Explain quantum computing in simple terms",
                "",
                "technology",
                "medium",
            ]
        )


def generate_prompts_toml(eval_root: Path, eval_name: str) -> None:
    """Generate prompts/default.toml template."""
    prompt_template = """v1 = '''
You are a helpful AI assistant.

User question: {{input}}

Please provide a clear, accurate answer.
'''
"""

    output_file = eval_root / eval_name / "prompts" / "default.toml"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write(prompt_template)


def create_directory_structure(eval_root: Path, eval_name: str) -> None:
    """Create the basic directory structure for an evaluation."""
    eval_dir = eval_root / eval_name

    # Create main directories
    (eval_dir / "config").mkdir(parents=True, exist_ok=True)
    (eval_dir / "data").mkdir(parents=True, exist_ok=True)
    (eval_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (eval_dir / "runs").mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (eval_dir / "config" / "judges").mkdir(parents=True, exist_ok=True)


def generate_all_templates(eval_root: Path, eval_name: str, eval_type: str) -> None:
    """Generate all template files for an evaluation."""
    with tracer.start_as_current_span("scaffolding.generate_all_templates") as span:
        span.set_attribute("eval_name", eval_name)
        span.set_attribute("eval_type", eval_type)

        create_directory_structure(eval_root, eval_name)
        generate_agents_config(eval_root, eval_name)
        generate_eval_config(eval_root, eval_name, eval_type)
        generate_async_config(eval_root, eval_name)
        generate_scenarios_json(eval_root, eval_name)
        generate_scenarios_csv(eval_root, eval_name)
        generate_prompts_toml(eval_root, eval_name)
