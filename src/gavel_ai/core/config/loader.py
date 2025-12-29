"""Configuration file loader with environment variable substitution."""
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, TypeVar

import toml
import yaml
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)

T = TypeVar("T", bound=BaseModel)


def substitute_env_vars(content: str) -> str:
    """Substitute {{VAR_NAME}} with environment variables.

    Args:
        content: String content with potential {{VAR}} placeholders

    Returns:
        Content with environment variables substituted

    Raises:
        ConfigError: If referenced environment variable is not set
    """
    pattern = r"\{\{([A-Z_][A-Z0-9_]*)\}\}"

    def replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        value = os.getenv(var_name)
        if value is None:
            raise ConfigError(
                f"Environment variable '{var_name}' not set - "
                f"Set {var_name} environment variable or provide value directly"
            )
        return value

    return re.sub(pattern, replace, content)


def load_config(
    config_path: Path,
    model: type[T],
    substitute_env: bool = True,
) -> T:
    """Load and validate configuration file.

    Args:
        config_path: Path to config file (.json, .yaml, .yml, or .toml)
        model: Pydantic model class to validate against
        substitute_env: Whether to substitute {{VAR}} environment variables

    Returns:
        Validated config model instance

    Raises:
        ConfigError: If file not found or invalid format
        ValidationError: If config fails Pydantic validation
    """
    with tracer.start_as_current_span("config.load_config") as span:
        span.set_attribute("config_path", str(config_path))
        span.set_attribute("model", model.__name__)

        # Check if file exists
        if not config_path.exists():
            raise ConfigError(
                f"Config file not found: {config_path} - Create file or check path"
            )

        # Read file content
        content = config_path.read_text()

        # Substitute environment variables
        if substitute_env:
            content = substitute_env_vars(content)

        # Parse based on file extension
        try:
            if config_path.suffix == ".json":
                data: Dict[str, Any] = json.loads(content)
            elif config_path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(content)
            elif config_path.suffix == ".toml":
                data = toml.loads(content)
            else:
                raise ConfigError(
                    f"Unsupported config format: {config_path.suffix} - "
                    f"Use .json, .yaml, or .toml"
                )
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Invalid JSON in {config_path} - Fix JSON syntax: {e}"
            ) from None
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in {config_path} - Fix YAML syntax: {e}"
            ) from None
        except toml.TomlDecodeError as e:
            raise ConfigError(
                f"Invalid TOML in {config_path} - Fix TOML syntax: {e}"
            ) from None

        # Validate with Pydantic
        try:
            return model.model_validate(data)
        except PydanticValidationError as e:
            raise ValidationError(
                f"Config validation failed in {config_path} - Fix validation errors: {e}"
            ) from None
