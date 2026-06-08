"""TuningAgent: LLM-as-meta-optimizer for autotune prompt iteration.

Generates an improved prompt version from the current prompt and aggregated
judge feedback by calling an LLM through the shared ProviderFactory, using a
{{var}}-templated meta-prompt (eval-local override or bundled fallback).
"""

import json
import re
from importlib.resources import files
from pathlib import Path
from typing import Any, Dict, List, Tuple

from gavel_ai.models.agents import ModelDefinition
from gavel_ai.providers.factory import ProviderFactory
from gavel_ai.telemetry import get_tracer

_PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")

_BUNDLED_META_PROMPT_PATH = files("gavel_ai") / "processors" / "autotune_template" / "autotune.toml"


def _render_meta_prompt(template_text: str, variables: Dict[str, Any]) -> str:
    """Substitute {{var}} placeholders; literal braces with unknown keys pass through unchanged."""

    def _replace(match: "re.Match[str]") -> str:
        key = match.group(1)
        if key in variables:
            return str(variables[key])
        return match.group(0)

    return _PLACEHOLDER_RE.sub(_replace, template_text)


def _load_meta_prompt_template(eval_dir: Path) -> str:
    """Load the meta-prompt template text: eval-local override, falling back to the bundled one."""
    import tomllib

    eval_local_path = eval_dir / "config" / "prompts" / "autotune.toml"
    if eval_local_path.exists():
        with open(eval_local_path, "rb") as f:
            data = tomllib.load(f)
    else:
        with _BUNDLED_META_PROMPT_PATH.open("rb") as f:
            data = tomllib.load(f)

    versions = [k for k in data.keys() if k.startswith("v")]
    if not versions:
        raise ValueError("Meta-prompt template has no versioned sections (e.g. [v1])")
    latest = max(versions, key=lambda v: int(v[1:]))
    return data[latest]["prompt"] if isinstance(data[latest], dict) else data[latest]


def _read_tuning_config(eval_dir: Path) -> Dict[str, Any]:
    """Best-effort read of the tuning block from config/eval_config.json (for template variables)."""
    config_path = eval_dir / "config" / "eval_config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("tuning") or {}
    except (OSError, json.JSONDecodeError):
        return {}


class TuningAgent:
    """LLM-as-meta-optimizer that rewrites prompts based on judge feedback."""

    def __init__(self, model_id: str, agents_config: Dict[str, Any], temperature: float = 0.7):
        """
        Args:
            model_id: Key into agents_config["_models"] identifying the model to use
            agents_config: Parsed agents.json content (with "_models" section)
            temperature: Temperature override for the TuningAgent's LLM calls
        """
        self.tracer = get_tracer(__name__)
        self.provider_factory = ProviderFactory()

        models = agents_config.get("_models", {})
        if model_id not in models:
            raise ValueError(f"TuningAgent model_id '{model_id}' not found in agents_config['_models']")

        model_data = dict(models[model_id])
        model_parameters = dict(model_data.get("model_parameters") or {})
        model_parameters["temperature"] = temperature
        model_data["model_parameters"] = model_parameters

        self.model_def: ModelDefinition = ModelDefinition.model_validate(model_data)
        self.agent = self.provider_factory.create_agent(self.model_def)

    async def generate_improved_prompt(
        self,
        current_prompt: str,
        judge_feedback: List[Dict[str, Any]],
        iteration: int,
        eval_dir: Path,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate an improved prompt version from feedback on the current version.

        Returns:
            Tuple of (improved_prompt_text, analysis_metadata) where analysis_metadata
            carries the raw provider call metadata (tokens, latency, provider/model).

        Raises:
            Exception: Any ProviderFactory failure propagates uncaught so that
                TuneStep.safe_execute() classifies it and applies the error policy.
        """
        with self.tracer.start_as_current_span("autotune.tune") as span:
            span.set_attribute("iteration", iteration)
            span.set_attribute("model", self.model_def.model_version)

            template_text = _load_meta_prompt_template(eval_dir)

            scores = [fb.get("score") for fb in judge_feedback if isinstance(fb.get("score"), (int, float))]
            avg_score = sum(scores) / len(scores) if scores else 0.0

            placeholder_vars = sorted(_PLACEHOLDER_RE.findall(current_prompt))
            tuning_config = _read_tuning_config(eval_dir)

            variables: Dict[str, Any] = {
                "current_prompt": current_prompt,
                "judge_feedback": json.dumps(judge_feedback),
                "avg_score": avg_score,
                "iteration": iteration,
                "max_rounds": tuning_config.get("max_rounds", "unknown"),
                "target_score": tuning_config.get("target_score") if tuning_config.get("target_score") is not None else "none",
                "placeholder_vars": ", ".join(f"{{{{{name}}}}}" for name in placeholder_vars),
            }

            rendered_prompt = _render_meta_prompt(template_text, variables)

            result = await self.provider_factory.call_agent(self.agent, rendered_prompt)

            span.set_attribute("output_length", len(result.output))

            return result.output.strip(), result.metadata
