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

from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.base import Step, StepPhase, ValidationResult
from gavel_ai.core.contexts import RunContext


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
            eval_config = context.eval_context.eval_config
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
            agents_config = context.eval_context.agents_config
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

        # DEC: this works for local prompt testing but not in-situ
        # TODO: remove this or refactor to handle in-situ
        # # 6. Validate first variant resolves to a model or agent
        # variant = eval_config.variants[0]
        #
        # # Check if variant is a model name in _models
        # if variant not in models:
        #     # Check if it's an agent name
        #     if variant not in agents_config:
        #         errors.append(f"variant '{variant}' not found in _models or agents")
        #         context.validation_result = ValidationResult(
        #             is_valid=False, errors=errors, warnings=warnings
        #         )
        #         raise ConfigError(
        #             f"Validation failed: variant '{variant}' not in _models or agents - "
        #             f"Add '{variant}' to _models or define as agent"
        #         )
        #     # If it's an agent, validate it has model_id
        #     agent = agents_config.get(variant, {})
        #     model_id = agent.get("model_id")
        #     if not model_id:
        #         errors.append(f"agent '{variant}' missing 'model_id' field")
        #         context.validation_result = ValidationResult(
        #             is_valid=False, errors=errors, warnings=warnings
        #         )
        #         raise ConfigError(
        #             f"Validation failed: agent '{variant}' missing 'model_id' - "
        #             f"Add 'model_id' referencing a model in _models"
        #         )
        #     if model_id not in models:
        #         errors.append(f"agent '{variant}' model_id '{model_id}' not found in _models")
        #         context.validation_result = ValidationResult(
        #             is_valid=False, errors=errors, warnings=warnings
        #         )
        #         raise ConfigError(
        #             f"Validation failed: model_id '{model_id}' not in _models - "
        #             f"Add '{model_id}' to _models or use existing model"
        #         )
        # else:
        #     model_id = variant

        # DC: this is only true for one-shot; may not be true for conv
        # TODO: remove this or refactor to handle workflows without scenarios
        # # 7. Validate scenarios not empty
        # try:
        #     scenarios = context.eval_context.scenarios
        #     if not scenarios:
        #         errors.append("No scenarios found")
        #         context.validation_result = ValidationResult(
        #             is_valid=False, errors=errors, warnings=warnings
        #         )
        #         raise ValidationError(
        #             "Validation failed: No scenarios found - "
        #             "Add scenarios to data/scenarios.json or scenarios.csv"
        #         )
        #     self.logger.debug(f"Loaded {len(scenarios)} scenarios")
        # except ConfigError as e:
        #     errors.append(f"Failed to load scenarios: {e}")
        #     context.validation_result = ValidationResult(
        #         is_valid=False, errors=errors, warnings=warnings
        #     )
        #     raise ConfigError(
        #         f"Validation failed: {errors[-1]} - "
        #         f"Check scenarios file exists and is valid"
        #     ) from e

        # All validations passed
        context.validation_result = ValidationResult(is_valid=True, errors=[], warnings=warnings)

        self.logger.info(f"Validation passed")
