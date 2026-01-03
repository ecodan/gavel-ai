"""Scaffolding functions for gavel oneshot create command."""
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
                "model_version": "claude-sonnet-4-5-20250929",
                "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                "provider_auth": {"api_key": "{{ANTHROPIC_API_KEY}}"},
            },
            "gpt-standard": {
                "model_provider": "openai",
                "model_family": "gpt",
                "model_version": "gpt-4o",
                "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                "provider_auth": {"api_key": "{{OPENAI_API_KEY}}"},
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
    """Generate eval_config.json template with nested async config."""
    eval_config: Dict[str, Any] = {
        "eval_type": "oneshot",
        "test_subject_type": "local",
        "eval_name": eval_name,
        "description": "Evaluation scaffolded by gavel oneshot create",
        "test_subjects": [
            {
                "prompt_name": "default",
                "judges": [
                    {
                        "id": "quality",
                        "deepeval_name": "deepeval.geval",
                        "config": {
                            "model": "gpt-4",
                            "criteria": "Evaluate the quality and accuracy of the response",
                            "evaluation_steps": [
                                "Check if the response is accurate",
                                "Verify completeness of answer",
                                "Assess clarity and usefulness",
                            ],
                        },
                    }
                ],
            }
        ],
        "variants": ["claude_standard"],
        "scenarios": {"source": "file.local", "name": "scenarios.json"},
        "execution": {"max_concurrent": 5},
        "async": {
            "num_workers": 8,
            "arrival_rate_per_sec": 20.0,
            "exec_rate_per_min": 100,
            "max_retries": 3,
            "task_timeout_seconds": 300,
            "stuck_timeout_seconds": 600,
            "emit_progress_interval_sec": 10,
        },
    }

    output_file = eval_root / eval_name / "config" / "eval_config.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(eval_config, f, indent=2)


def generate_scenarios_json(eval_root: Path, eval_name: str) -> None:
    """Generate scenarios.json template with sample scenarios."""
    scenarios_data = [
        {
            "scenario_id": "scenario-1",
            "input": "What is the capital of France?",
            "expected": "Paris",
            "metadata": {"category": "geography", "difficulty": "easy"},
        },
        {
            "scenario_id": "scenario-2",
            "input": "Explain quantum computing in simple terms",
            "expected": "",
            "metadata": {"category": "technology", "difficulty": "medium"},
        },
    ]

    output_file = eval_root / eval_name / "data" / "scenarios.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(scenarios_data, f, indent=2)


def generate_prompts_toml(eval_root: Path, eval_name: str) -> None:
    """Generate config/prompts/default.toml template."""
    prompt_template = """v1 = '''
You are a helpful AI assistant.

User question: {{input}}

Please provide a clear, accurate answer.
'''
"""

    output_file = eval_root / eval_name / "config" / "prompts" / "default.toml"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write(prompt_template)


def create_directory_structure(eval_root: Path, eval_name: str) -> None:
    """Create the basic directory structure for an evaluation."""
    eval_dir = eval_root / eval_name

    # Create main directories
    (eval_dir / "config").mkdir(parents=True, exist_ok=True)
    (eval_dir / "data").mkdir(parents=True, exist_ok=True)
    (eval_dir / "runs").mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (eval_dir / "config" / "judges").mkdir(parents=True, exist_ok=True)
    (eval_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)


def generate_all_templates(eval_root: Path, eval_name: str, eval_type: str) -> None:
    """Generate all template files for an evaluation."""
    with tracer.start_as_current_span("scaffolding.generate_all_templates") as span:
        span.set_attribute("eval_name", eval_name)
        span.set_attribute("eval_type", eval_type)

        create_directory_structure(eval_root, eval_name)
        generate_agents_config(eval_root, eval_name)
        generate_eval_config(eval_root, eval_name, eval_type)
        generate_scenarios_json(eval_root, eval_name)
        generate_prompts_toml(eval_root, eval_name)
