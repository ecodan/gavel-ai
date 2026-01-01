"""Config loader orchestration for CLI workflows.

Provides simple ConfigLoader class that orchestrates loading of all
configuration files needed for a OneShot evaluation run.

Uses existing config infrastructure from Epic 2.
"""
import toml
from pathlib import Path
from typing import Any, Dict, List

from gavel_ai.core.config.agents import AgentsFile, validate_agent_references
from gavel_ai.core.config.loader import load_config
from gavel_ai.core.config.models import AsyncConfig, EvalConfig
from gavel_ai.core.config.scenarios import Scenario, load_scenarios
from gavel_ai.core.exceptions import ConfigError


class ConfigLoader:
    """
    Orchestrates loading of all configuration files for evaluation.

    Simple wrapper that coordinates loading of:
    - eval_config.json: Evaluation configuration
    - async_config.json: Async execution settings
    - agents.json: Model and agent definitions
    - scenarios.json or scenarios.csv: Test scenarios
    - prompts/*.toml: Prompt templates
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
        self.prompts_dir = self.eval_dir / "prompts"

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
                f"Run 'gavel oneshot create' or add async_config.json"
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
                f"Scenarios file not found in {self.data_dir} - "
                f"Add scenarios.json or scenarios.csv"
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
                f"Add {prompt_name}.toml to prompts directory"
            )

        # Load TOML file
        try:
            with open(prompt_file, "r") as f:
                prompt_data = toml.load(f)
        except Exception as e:
            raise ConfigError(
                f"Invalid TOML in {prompt_file} - Fix TOML syntax: {e}"
            ) from None

        # Get version
        if version not in prompt_data:
            available = ", ".join(prompt_data.keys())
            raise ConfigError(
                f"Prompt version '{version}' not found in {prompt_file} - "
                f"Available versions: {available}"
            )

        return prompt_data[version]
