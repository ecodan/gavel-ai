"""Scaffolding functions for gavel oneshot create command."""

import json
from pathlib import Path
from typing import Any, Dict

from gavel_ai.core.exceptions import ConfigError


def generate_agents_config(eval_root: Path, eval_name: str) -> None:
    """Generate agents.json template with sensible defaults."""
    agents_config: Dict[str, Any] = {
        "_models": {
            "claude-haiku": {
                "model_provider": "anthropic",
                "model_family": "claude",
                "model_version": "claude-haiku-4-5-20251001",
                "model_parameters": {"temperature": 0.3, "max_tokens": 4096},
                "provider_auth": {"api_key": "{{ANTHROPIC_API_KEY}}"},
            },
            "gpt-5-mini": {
                "model_provider": "openai",
                "model_family": "gpt",
                "model_version": "gpt-5-mini-2025-08-07",
                "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                "provider_auth": {"api_key": "{{OPENAI_API_KEY}}"},
            },
        },
        "claude_haiku": {"model_id": "claude-haiku", "prompt": "assistant:v1"},
        "assistant_agent": {"model_id": "claude-haiku", "prompt": "assistant:v1"},
    }

    output_file = eval_root / eval_name / "config" / "agents.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(agents_config, f, indent=2)


def generate_eval_config(eval_root: Path, eval_name: str, eval_type: str) -> None:
    """Generate eval_config.json template with nested async config."""
    if eval_type == "in-situ":
        eval_config: Dict[str, Any] = {
            "eval_type": "oneshot",
            "test_subject_type": "in-situ",
            "eval_name": eval_name,
            "description": "In-situ evaluation scaffolded by gavel oneshot create",
            "test_subjects": [
                {
                    "system_id": "my-system",
                    "protocol": "open_ai",
                    "config": {
                        "endpoint": "http://localhost:8080/v1/chat/completions",
                        "model": "my-model",
                    },
                    "judges": [
                        {
                            "name": "quality",
                            "type": "deepeval.geval",
                            "config": {
                                "model": "gpt-5-mini",
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
            "variants": ["claude_haiku"],
            "scenarios": {
                "source": "file.local",
                "name": "scenarios.json",
                "field_mapping": {"expected_output": "expected_behavior"},
            },
            "execution": {"max_concurrent": 10},
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
    else:
        eval_config = {
            "eval_type": "oneshot",
            "test_subject_type": "local",
            "eval_name": eval_name,
            "description": "Evaluation scaffolded by gavel oneshot create",
            "test_subjects": [
                {
                    "prompt_name": "assistant",
                    "judges": [
                        {
                            "name": "quality",
                            "type": "deepeval.geval",
                            "config": {
                                "model": "gpt-5-mini",
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
            "variants": ["claude_haiku"],
            "scenarios": {
                "source": "file.local",
                "name": "scenarios.json",
                "field_mapping": {"expected_output": "expected_behavior"},
            },
            "execution": {"max_concurrent": 10},
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
            "scenario_id": "1",
            "input": "What is the capital of France?",
            "expected": "Paris",
            "metadata": {"category": "geography", "difficulty": "easy"},
        },
        {
            "scenario_id": "2",
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
    """Generate config/prompts/assistant.toml template."""
    prompt_template = """v1 = '''
You are a helpful AI assistant.

User question: {{input}}

Provide a short, clear, accurate answer.
'''
"""

    output_file = eval_root / eval_name / "config" / "prompts" / "assistant.toml"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write(prompt_template)


def _generate_quality_judge_toml(eval_root: Path, eval_name: str) -> None:
    """Generate example config/judges/quality_judge.toml for all scaffold paths."""
    quality_judge = """# Example TOML-based judge config.
# Reference this in eval_config.json via: "config_ref": "quality_judge"
# Fields here are merged into the judge config at run time.

criteria = "Evaluate the quality and accuracy of the response"
threshold = 0.7

evaluation_steps = [
    "Check if the response directly answers the question",
    "Verify the response is factually accurate",
    "Assess clarity and conciseness",
]
"""

    output_file = eval_root / eval_name / "config" / "judges" / "quality_judge.toml"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write(quality_judge)


def create_directory_structure(eval_root: Path, eval_name: str) -> None:
    """Create the basic directory structure for an evaluation."""
    eval_dir = eval_root / eval_name

    (eval_dir / "config").mkdir(parents=True, exist_ok=True)
    (eval_dir / "data").mkdir(parents=True, exist_ok=True)
    (eval_dir / "runs").mkdir(parents=True, exist_ok=True)
    (eval_dir / "config" / "judges").mkdir(parents=True, exist_ok=True)
    (eval_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)


def _generate_classification_templates(eval_root: Path, eval_name: str, eval_type: str) -> None:
    """Generate classification-specific templates."""
    eval_config: Dict[str, Any] = {
        "eval_type": "oneshot",
        "test_subject_type": "local",
        "eval_name": eval_name,
        "description": "Classification evaluation scaffolded by gavel oneshot create",
        "test_subjects": [
            {
                "prompt_name": "classifier",
                "judges": [
                    {
                        "name": "label_accuracy",
                        "type": "classifier",
                        "config": {
                            "prediction_field": "label",
                            "actual_field": "expected",
                            "report_metric": "accuracy",
                        },
                    },
                    {
                        "name": "label_f1",
                        "type": "classifier",
                        "config": {
                            "prediction_field": "label",
                            "actual_field": "expected",
                            "report_metric": "f1",
                        },
                    },
                ],
            }
        ],
        "variants": ["claude_haiku"],
        "scenarios": {"source": "file.local", "name": "scenarios.json"},
        "execution": {"max_concurrent": 10},
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
    with open(output_file, "w") as f:
        json.dump(eval_config, f, indent=2)

    scenarios_data = [
        {
            "scenario_id": "cls-1",
            "input": {"text": "I absolutely loved this product! Best purchase ever.", "expected": "positive"},
            "metadata": {"category": "sentiment"},
        },
        {
            "scenario_id": "cls-2",
            "input": {"text": "This was okay, nothing special.", "expected": "neutral"},
            "metadata": {"category": "sentiment"},
        },
        {
            "scenario_id": "cls-3",
            "input": {"text": "Terrible quality, broke after one day.", "expected": "positive"},
            "metadata": {"category": "sentiment", "note": "intentionally wrong expected for testing"},
        },
    ]

    scenarios_file = eval_root / eval_name / "data" / "scenarios.json"
    with open(scenarios_file, "w") as f:
        json.dump(scenarios_data, f, indent=2)

    prompt_template = """v1 = '''
You are a sentiment classifier. Classify the following text as positive, neutral, or negative.
Respond with ONLY a JSON object in this exact format: {"label": "<sentiment>"}

Text: {{input.text}}
'''
"""

    prompt_file = eval_root / eval_name / "config" / "prompts" / "classifier.toml"
    with open(prompt_file, "w") as f:
        f.write(prompt_template)


def _generate_regression_templates(eval_root: Path, eval_name: str, eval_type: str) -> None:
    """Generate regression-specific templates."""
    eval_config: Dict[str, Any] = {
        "eval_type": "oneshot",
        "test_subject_type": "local",
        "eval_name": eval_name,
        "description": "Regression evaluation scaffolded by gavel oneshot create",
        "test_subjects": [
            {
                "prompt_name": "regressor",
                "judges": [
                    {
                        "name": "value_mae",
                        "type": "regression",
                        "config": {
                            "prediction_field": "value",
                            "actual_field": "expected",
                            "report_metric": "mean_absolute_error",
                        },
                    }
                ],
            }
        ],
        "variants": ["claude_haiku"],
        "scenarios": {"source": "file.local", "name": "scenarios.json"},
        "execution": {"max_concurrent": 10},
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
    with open(output_file, "w") as f:
        json.dump(eval_config, f, indent=2)

    scenarios_data = [
        {
            "scenario_id": "reg-1",
            "input": {"question": "What is 15% of 200?", "expected": "30.0"},
            "metadata": {"category": "arithmetic"},
        },
        {
            "scenario_id": "reg-2",
            "input": {"question": "What is the square root of 144?", "expected": "12.0"},
            "metadata": {"category": "arithmetic"},
        },
        {
            "scenario_id": "reg-3",
            "input": {"question": "What is 7 times 8?", "expected": "55.0"},
            "metadata": {"category": "arithmetic", "note": "intentionally wrong expected for testing"},
        },
    ]

    scenarios_file = eval_root / eval_name / "data" / "scenarios.json"
    with open(scenarios_file, "w") as f:
        json.dump(scenarios_data, f, indent=2)

    prompt_template = """v1 = '''
You are a precise calculator. Answer the following arithmetic question.
Respond with ONLY a JSON object in this exact format: {"value": <number>}

Question: {{input.question}}
'''
"""

    prompt_file = eval_root / eval_name / "config" / "prompts" / "regressor.toml"
    with open(prompt_file, "w") as f:
        f.write(prompt_template)


def _generate_default_templates(eval_root: Path, eval_name: str, eval_type: str) -> None:
    """Generate default templates (existing behavior)."""
    generate_eval_config(eval_root, eval_name, eval_type)
    if eval_type != "in-situ":
        generate_scenarios_json(eval_root, eval_name)
        generate_prompts_toml(eval_root, eval_name)
    else:
        generate_scenarios_json(eval_root, eval_name)


def _generate_conversational_templates(eval_root: Path, eval_name: str, eval_type: str) -> None:
    """Generate conversational evaluation templates with conv_completeness and conv_geval judges."""
    eval_config: Dict[str, Any] = {
        "eval_type": "oneshot",
        "workflow_type": "conversational",
        "test_subject_type": "local",
        "eval_name": eval_name,
        "description": "Conversational evaluation scaffolded by gavel oneshot create",
        "test_subjects": [
            {
                "prompt_name": "assistant",
                "judges": [
                    {
                        "name": "conversation_completeness",
                        "type": "deepeval.conversation_completeness",
                        "threshold": 0.75,
                        "config": {"model": "gpt-5-mini"},
                    },
                    {
                        "name": "conversational_quality",
                        "type": "deepeval.conversational_geval",
                        "threshold": 0.7,
                        "config": {
                            "model": "gpt-5-mini",
                            "criteria": "Evaluate the quality and coherence of the conversation",
                            "evaluation_steps": [
                                "Check if the assistant addresses the user's goals",
                                "Evaluate response relevance across turns",
                                "Assess overall conversation coherence",
                            ],
                        },
                    },
                ],
            }
        ],
        "variants": ["claude_haiku"],
        "scenarios": {
            "source": "file.local",
            "name": "scenarios.json",
        },
        "conversational": {
            "max_turns": 10,
            "max_turn_length": 2000,
            "turn_generator": {"model_id": "claude_haiku", "temperature": 0.0, "max_tokens": 500},
        },
        "execution": {"max_concurrent": 5},
    }

    output_file = eval_root / eval_name / "config" / "eval_config.json"
    with open(output_file, "w") as f:
        json.dump(eval_config, f, indent=2)

    scenarios_data = [
        {
            "scenario_id": "conv-1",
            "input": "Help me plan a trip to Japan for two weeks.",
            "metadata": {"category": "travel_planning", "difficulty": "medium"},
        },
        {
            "scenario_id": "conv-2",
            "input": "I need help debugging a Python script that reads CSV files.",
            "metadata": {"category": "technical_support", "difficulty": "medium"},
        },
    ]

    scenarios_file = eval_root / eval_name / "data" / "scenarios.json"
    with open(scenarios_file, "w") as f:
        json.dump(scenarios_data, f, indent=2)

    prompt_template = """v1 = '''
You are a helpful AI assistant. Engage in a natural, helpful conversation with the user.
Provide clear, accurate, and actionable responses.

User message: {{input}}
'''
"""

    prompt_file = eval_root / eval_name / "config" / "prompts" / "assistant.toml"
    with open(prompt_file, "w") as f:
        f.write(prompt_template)


def generate_all_templates(
    eval_root: Path, eval_name: str, eval_type: str, template: str = "default"
) -> None:
    """
    Generate all template files for an evaluation.

    Args:
        eval_root: Root directory for evaluations.
        eval_name: Name of the evaluation.
        eval_type: Evaluation type: "local" or "in-situ".
        template: Scaffold template: "default", "classification", "regression", or "conversational".
            - ``default``: General-purpose LLM judge scaffold.
            - ``classification``: Classifier metrics with sentiment example scenarios.
            - ``regression``: Regression metric with arithmetic example scenarios.
            - ``conversational``: Multi-turn eval with conversation_completeness and conversational_geval.
            Note: ``--type in-situ`` skips prompt generation and uses remote endpoint structure.

    Raises:
        ConfigError: If template name is not recognized.
    """
    create_directory_structure(eval_root, eval_name)
    generate_agents_config(eval_root, eval_name)

    if template == "classification":
        _generate_classification_templates(eval_root, eval_name, eval_type)
    elif template == "regression":
        _generate_regression_templates(eval_root, eval_name, eval_type)
    elif template == "conversational":
        _generate_conversational_templates(eval_root, eval_name, eval_type)
    elif template == "default":
        _generate_default_templates(eval_root, eval_name, eval_type)
    else:
        raise ConfigError(
            f"Unknown template '{template}' - Available: default, classification, regression, conversational"
        )

    _generate_quality_judge_toml(eval_root, eval_name)
