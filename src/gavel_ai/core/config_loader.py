"""Config loader orchestration for CLI workflows.

Provides simple ConfigLoader class that orchestrates loading of all
configuration files needed for a OneShot evaluation run.

Uses existing config infrastructure from Epic 2.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import toml

from gavel_ai.core.config.agents import AgentsFile, validate_agent_references
from gavel_ai.core.config.loader import load_config
from gavel_ai.core.config.models import AsyncConfig, EvalConfig
from gavel_ai.core.config.scenarios import Scenario, load_scenarios
from gavel_ai.core.exceptions import ConfigError


class ConfigLoader:
    """
    Orchestrates loading of all configuration files for evaluation.

    Simple wrapper that coordinates loading of:
    - eval_config.json: Evaluation configuration (includes nested async config)
    - agents.json: Model and agent definitions
    - scenarios.json or scenarios.csv: Test scenarios
    - config/prompts/*.toml: Prompt templates
    """

    def __init__(self, eval_root: Path, eval_name: str):
        """
        Initialize config loader.

        Args:
            eval_root: Root directory for evaluations (e.g., .gavel/evaluations)
            eval_name: Name of the evaluation
        """
        self.eval_root = Path(eval_root)
        self.eval_name = eval_name
        self.eval_dir = self.eval_root / eval_name
        self.config_dir = self.eval_dir / "config"
        self.data_dir = self.eval_dir / "data"
        self.prompts_dir = self.config_dir / "prompts"

    def load_eval_config(self) -> EvalConfig:
        """
        Load and validate eval_config.json.

        Returns:
            EvalConfig: Validated evaluation configuration

        Raises:
            ConfigError: If file not found or invalid
            ValidationError: If validation fails
        """
        config_file = self.config_dir / "eval_config.json"

        if not config_file.exists():
            raise ConfigError(
                f"Evaluation '{self.eval_name}' not found - "
                f"Run 'gavel oneshot create --eval {self.eval_name}' first"
            )

        return load_config(config_file, EvalConfig)

    def load_async_config(self) -> AsyncConfig:
        """
        Load and validate async_config.json.

        Note: Deprecated. Async config is now nested in eval_config.json.
        This method is kept for backward compatibility with legacy configs.

        Returns:
            AsyncConfig: Validated async configuration

        Raises:
            ConfigError: If file not found or invalid
            ValidationError: If validation fails
        """
        config_file = self.config_dir / "async_config.json"

        if not config_file.exists():
            raise ConfigError(
                f"Config file not found: {config_file} - "
                f"Async configuration is now nested in eval_config.json. "
                f"Run 'gavel oneshot create' to generate the correct structure."
            )

        return load_config(config_file, AsyncConfig)

    def load_agents_config(self) -> Dict[str, Any]:
        """
        Load and validate agents.json.

        Returns:
            Dict[str, Any]: Raw agents configuration dict

        Raises:
            ConfigError: If file not found or invalid
            ValidationError: If validation fails
        """
        agents_file = self.config_dir / "agents.json"

        if not agents_file.exists():
            raise ConfigError(
                f"Config file not found: {agents_file} - "
                f"Run 'gavel oneshot create' or add agents.json"
            )

        # Load and validate with AgentsFile model
        agents_config = load_config(agents_file, AgentsFile)

        # Validate agent references
        validate_agent_references(agents_config)

        # Return as dict for easier access
        return agents_config.model_dump(by_alias=True)

    def load_scenarios(self) -> List[Scenario]:
        """
        Load scenarios from scenarios.json or scenarios.csv.

        Returns:
            List[Scenario]: List of scenario objects

        Raises:
            ConfigError: If file not found or invalid
            ValidationError: If validation fails
        """
        # Try JSON first, then CSV
        json_file = self.data_dir / "scenarios.json"
        csv_file = self.data_dir / "scenarios.csv"

        if json_file.exists():
            scenarios_file = json_file
        elif csv_file.exists():
            scenarios_file = csv_file
        else:
            raise ConfigError(
                f"Scenarios file not found in {self.data_dir} - Add scenarios.json or scenarios.csv"
            )

        return load_scenarios(scenarios_file)

    def load_prompt_template(self, prompt_ref: str = "default:v1") -> str:
        """
        Load prompt template from TOML file.

        Args:
            prompt_ref: Prompt reference in format "name:version" (default: "default:v1")

        Returns:
            str: Prompt template content

        Raises:
            ConfigError: If prompt file or version not found
        """
        # Parse prompt reference
        parts = prompt_ref.split(":")
        if len(parts) != 2:
            raise ConfigError(
                f"Invalid prompt reference '{prompt_ref}' - "
                f"Use format 'name:version' (e.g., 'default:v1')"
            )

        prompt_name, version = parts
        prompt_file = self.prompts_dir / f"{prompt_name}.toml"

        if not prompt_file.exists():
            raise ConfigError(
                f"Prompt file not found: {prompt_file} - "
                f"Add {prompt_name}.toml to config/prompts/ directory"
            )

        # Load TOML file
        try:
            with open(prompt_file, "r") as f:
                prompt_data = toml.load(f)
        except Exception as e:
            raise ConfigError(f"Invalid TOML in {prompt_file} - Fix TOML syntax: {e}") from None

        # Get version
        if version not in prompt_data:
            available = ", ".join(prompt_data.keys())
            raise ConfigError(
                f"Prompt version '{version}' not found in {prompt_file} - "
                f"Available versions: {available}"
            )

        return prompt_data[version]


def resolve_model_id(agents_config: Dict[str, Any], model_id: str) -> str:
    """
    Resolve custom model ID to actual model version string.

    This function maps custom model identifiers (defined in agents.json _models)
    to their actual model version strings recognized by third-party libraries
    like DeepEval. If the model_id is not found in _models, it's assumed to be
    a standard model name (e.g., "gpt-4o") and passed through unchanged.

    Args:
        agents_config: Loaded agents configuration dict containing _models definitions
        model_id: Model identifier to resolve (custom ID or standard name)

    Returns:
        str: Resolved actual model version string

    Raises:
        ConfigError: If model_id is in _models but missing model_version field

    Examples:
        >>> agents_config = {
        ...     "_models": {
        ...         "claude_standard": {
        ...             "model_version": "claude-sonnet-4-5-20250929"
        ...         }
        ...     }
        ... }
        >>> resolve_model_id(agents_config, "claude_standard")
        'claude-sonnet-4-5-20250929'

        >>> resolve_model_id(agents_config, "gpt-4o")  # Standard name passes through
        'gpt-4o'
    """
    models: Dict[str, Any] = agents_config.get("_models", {})

    # If model_id is in _models, it's a custom ID - resolve it
    if model_id in models:
        model_version: Optional[str] = models[model_id].get("model_version")
        if not model_version:
            raise ConfigError(
                f"Model '{model_id}' in _models is missing 'model_version' field - "
                f"Add 'model_version' to the model definition in agents.json"
            )
        return model_version

    # Otherwise, assume it's already a real model name - pass through
    return model_id


def get_model_definition(agents_config: Dict[str, Any], model_id: str) -> Dict[str, Any]:
    """
    Get the full model definition including provider and family info.

    This function looks up a model in the agents config and returns the complete
    definition including model_provider, model_family, and model_version.
    If model_id is not in _models, returns a minimal definition with only the
    model_version (assumed to be a standard model name).

    Args:
        agents_config: Loaded agents configuration dict containing _models definitions
        model_id: Model identifier to resolve (custom ID or standard name)

    Returns:
        dict: Model definition with keys:
            - model_version: Actual model identifier (required)
            - model_provider: Provider name (optional, None for standard names)
            - model_family: Model family (optional, None for standard names)

    Raises:
        ConfigError: If model_id is in _models but missing model_version field
    """
    models: Dict[str, Any] = agents_config.get("_models", {})

    # If model_id is in _models, it's a custom ID - return full definition
    if model_id in models:
        model_def = models[model_id]
        model_version: Optional[str] = model_def.get("model_version")
        if not model_version:
            raise ConfigError(
                f"Model '{model_id}' in _models is missing 'model_version' field - "
                f"Add 'model_version' to the model definition in agents.json"
            )
        return {
            "model_version": model_version,
            "model_provider": model_def.get("model_provider"),
            "model_family": model_def.get("model_family"),
        }

    # Otherwise, assume it's already a real model name - return minimal definition
    return {
        "model_version": model_id,
        "model_provider": None,
        "model_family": None,
    }
