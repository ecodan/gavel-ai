"""
Validator step for OneShot workflow.

Validates all configurations before execution:
- eval_config loadable and valid
- agents.json exists and has _models + subject_agent
- scenarios list not empty
- subject_agent model_id resolves in _models
- prompts exist for referenced test_subjects

Per Tech Spec 3.9: Extracted from run() lines 126-143.
"""

import logging
from typing import List

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.core.steps.base import Step, StepPhase, ValidationResult


class ValidatorStep(Step):
    """
    Validates all configurations before workflow execution.

    Sets context.validation_result with validation outcome.
    """

    def __init__(self, logger: logging.Logger):
        super().__init__(logger)

    @property
    def phase(self) -> StepPhase:
        return StepPhase.VALIDATION

    async def execute(self, context: RunContext) -> None:
        """
        Validate all configs.

        Args:
            context: RunContext for reading configs and writing validation result

        Raises:
            ConfigError: If config loading fails
            ValidationError: If validation fails
        """
        errors: List[str] = []
        warnings: List[str] = []

        self.logger.info(f"Validating configuration for '{context.eval_context.eval_name}'")

        # 1. Validate eval_config loadable
        try:
            eval_config = context.eval_context.eval_config.read()
            self.logger.debug(
                f"eval_config loaded: test_subject_type={eval_config.test_subject_type}"
            )
        except ConfigError as e:
            errors.append(f"Failed to load eval_config: {e}")
            context.validation_result = ValidationResult(
                is_valid=False, errors=errors, warnings=warnings
            )
            raise ConfigError(
                f"Validation failed: {errors[0]} - Check eval_config.json exists and is valid"
            ) from e

        # 2. Validate agents.json exists and has required sections
        try:
            agents_config = context.eval_context.agents.read()
            self.logger.debug("agents.json loaded")
        except ConfigError as e:
            errors.append(f"Failed to load agents.json: {e}")
            context.validation_result = ValidationResult(
                is_valid=False, errors=errors, warnings=warnings
            )
            raise ConfigError(
                f"Validation failed: {errors[0]} - Check agents.json exists and is valid"
            ) from e

        # 3. Validate _models section exists
        models = agents_config.get("_models", {})
        if not models:
            errors.append("agents.json missing '_models' section")
            context.validation_result = ValidationResult(
                is_valid=False, errors=errors, warnings=warnings
            )
            raise ConfigError(
                "Validation failed: agents.json missing '_models' section - "
                "Add '_models' with model definitions"
            )

        # 4. Validate test_subjects exist and not empty
        if not eval_config.test_subjects:
            errors.append("eval_config missing 'test_subjects' or empty")
            context.validation_result = ValidationResult(
                is_valid=False, errors=errors, warnings=warnings
            )
            raise ConfigError(
                "Validation failed: eval_config missing 'test_subjects' - "
                "Add at least one test subject"
            )

        # 5. Validate variants exist and not empty
        if not eval_config.variants:
            errors.append("eval_config missing 'variants' or empty")
            context.validation_result = ValidationResult(
                is_valid=False, errors=errors, warnings=warnings
            )
            raise ConfigError(
                "Validation failed: eval_config missing 'variants' - Add at least one variant"
            )

        # 6. Validate variants resolve to models or agents (local evals only)
        if eval_config.test_subject_type == "local":
            for variant in eval_config.variants:
                if variant not in models:
                    if variant not in agents_config:
                        errors.append(f"variant '{variant}' not found in _models or agents")
                        context.validation_result = ValidationResult(
                            is_valid=False, errors=errors, warnings=warnings
                        )
                        raise ConfigError(
                            f"Validation failed: variant '{variant}' not in _models or agents - "
                            f"Add '{variant}' to _models or define as agent"
                        )
                    agent = agents_config.get(variant, {})
                    model_id = agent.get("model_id")
                    if not model_id or model_id not in models:
                        errors.append(f"agent '{variant}' model_id not found in _models")
                        context.validation_result = ValidationResult(
                            is_valid=False, errors=errors, warnings=warnings
                        )
                        raise ConfigError(
                            f"Validation failed: agent '{variant}' model_id not in _models - "
                            f"Add or fix model_id in agents.json"
                        )

        # 7. Validate prompts exist for each test_subject (local evals only)
        if eval_config.test_subject_type == "local":
            for subject in eval_config.test_subjects:
                if subject.prompt_name:
                    try:
                        context.eval_context.get_prompt(f"{subject.prompt_name}:latest")
                    except Exception:
                        errors.append(f"Prompt '{subject.prompt_name}' not found in config/prompts/")
                        context.validation_result = ValidationResult(
                            is_valid=False, errors=errors, warnings=warnings
                        )
                        raise ConfigError(
                            f"Validation failed: prompt '{subject.prompt_name}' not found - "
                            f"Add config/prompts/{subject.prompt_name}.toml"
                        )

        # 8. Warn for unregistered judge types (no raise - advisory only)
        from gavel_ai.judges.judge_registry import JudgeRegistry
        available_judges = set(JudgeRegistry.list_available())
        for subject in eval_config.test_subjects:
            for judge in (subject.judges or []):
                if judge.type not in available_judges:
                    warnings.append(f"Judge type '{judge.type}' is not registered in JudgeRegistry")
                    self.logger.warning(
                        f"Judge type '{judge.type}' is not registered - may fail at runtime"
                    )

        # 9. Validate scenarios not empty and IDs are unique
        try:
            scenarios = context.eval_context.scenarios.read()
            if not scenarios:
                errors.append("No scenarios found")
                context.validation_result = ValidationResult(
                    is_valid=False, errors=errors, warnings=warnings
                )
                raise ValidationError(
                    "Validation failed: No scenarios found - "
                    "Add scenarios to data/scenarios.json"
                )
            ids = [s.scenario_id for s in scenarios]
            seen: set[str] = set()
            duplicates: List[str] = []
            for sid in ids:
                if sid in seen:
                    duplicates.append(sid)
                seen.add(sid)
            if duplicates:
                errors.append(f"Duplicate scenario IDs: {duplicates}")
                context.validation_result = ValidationResult(
                    is_valid=False, errors=errors, warnings=warnings
                )
                raise ConfigError(
                    f"Validation failed: duplicate scenario IDs {duplicates} - "
                    f"Each scenario must have a unique id"
                )
        except (ValidationError, ConfigError):
            raise
        except Exception:
            pass  # Scenarios may not be present for all workflow types

        # All validations passed
        context.validation_result = ValidationResult(is_valid=True, errors=[], warnings=warnings)

        self.logger.info("Validation passed")
