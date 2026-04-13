"""
GenerateStep for creating conversational scenarios via LLM generation.

Implements scenario generation from prompts using LLM with configurable output.
Follows the Step abstraction for integration into conversational workflows.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, cast

import toml

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ProcessorError, ValidationError
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.providers.factory import ProviderFactory


class GenerateStep(Step):
    """
    Generate conversational scenarios from prompt files using LLM.

    Creates scenarios.jsonl with generated scenarios following the conversational
    evaluation schema. Each scenario includes id, user_goal (required),
    context (optional), and dialogue_guidance (optional).
    """

    def __init__(self, logger: logging.Logger):
        """Initialize GenerateStep with logger."""
        super().__init__(logger)

    @property
    def phase(self) -> StepPhase:
        """Return the workflow phase for this step."""
        return StepPhase.SCENARIO_PROCESSING

    async def execute(self, context: RunContext) -> None:
        """
        Execute scenario generation.

        Args:
            context: RunContext for reading configs and writing outputs

        Raises:
            ProcessorError: On generation failures
            ValidationError: On configuration issues
        """
        with self.tracer.start_as_current_span("generate.execute") as span:
            try:
                # Load prompt configuration
                prompt_config = self._load_prompt_config(context)
                span.set_attribute("generate.prompt_file", str(prompt_config["file_path"]))

                # Generate scenarios using LLM
                scenarios = await self._generate_scenarios(prompt_config, context)
                span.set_attribute("generate.scenario_count", len(scenarios))
                span.set_attribute("generate.model_id", prompt_config["model_id"])

                # Save scenarios to JSONL file
                output_path = self._save_scenarios(scenarios, context)
                span.set_attribute("generate.output_file", str(output_path))

                self.logger.info(f"Generated {len(scenarios)} scenarios to {output_path}")

            except Exception as e:
                self.logger.error(f"Scenario generation failed: {e}", exc_info=True)
                raise ProcessorError(
                    f"Scenario generation failed: {e} - "
                    f"Check prompt file format and LLM configuration"
                ) from e

    def _load_prompt_config(self, context: RunContext) -> Dict[str, Any]:
        """
        Load prompt configuration from TOML file.

        Args:
            context: RunContext with eval configuration

        Returns:
            Dictionary with prompt configuration

        Raises:
            ValidationError: If prompt file is missing or invalid
        """
        # Get prompt file path from config or use default
        config_data = context.eval_context.eval_config.read()
        prompt_path = config_data.get("scenario_generation", {}).get("prompt_file")
        prompt_file = Path(prompt_path) if prompt_path else Path("prompts/generate_scenarios.toml")

        if not prompt_file.exists():
            raise ValidationError(
                f"Prompt file not found: {prompt_file} - "
                f"Create prompts/generate_scenarios.toml with scenario generation prompt"
            )

        try:
            with prompt_file.open("r", encoding="utf-8") as f:
                config = toml.load(f)

            # Validate required fields
            if "prompt" not in config:
                raise ValidationError(
                    f"Missing 'prompt' field in {prompt_file} - "
                    f"Add prompt template for scenario generation"
                )

            return {
                "file_path": prompt_file,
                "prompt": config["prompt"],
                "count": config.get("count", 5),
                "model_id": config.get("model_id", "claude-standard"),
            }

        except Exception as e:
            raise ValidationError(
                f"Invalid TOML format in {prompt_file}: {e} - Fix TOML syntax and structure"
            ) from e

    async def _generate_scenarios(
        self, prompt_config: Dict[str, Any], context: RunContext
    ) -> List[Dict[str, Any]]:
        """
        Generate scenarios using LLM.

        Args:
            prompt_config: Configuration with prompt and generation settings
            context: RunContext for LLM access

        Returns:
            List of scenario dictionaries

        Raises:
            ProcessorError: On LLM generation failures
        """
        # Load agents configuration to access model definitions
        try:
            agents_config = context.eval_context.agents.read()
        except Exception as e:
            raise ProcessorError(
                f"Failed to load agents configuration: {e} - "
                f"Check agents.json format and ensure model '{prompt_config['model_id']}' is defined"
            ) from e

        # Get model definition from agents config
        models = agents_config.get("_models", {})
        model_id = prompt_config["model_id"]

        if model_id not in models:
            raise ProcessorError(
                f"Model '{model_id}' not found in agents configuration - "
                f"Add model definition to _models section or use existing model_id"
            )

        # Create ModelDefinition with temperature=0 for deterministic output
        model_data = models[model_id].copy()
        model_parameters = model_data.get("model_parameters", {})
        model_parameters["temperature"] = 0  # Ensure deterministic generation per AC4

        model_def = ModelDefinition.model_validate(
            {**model_data, "model_parameters": model_parameters}
        )

        # Create ProviderFactory and agent
        try:
            provider_factory = ProviderFactory()
            agent = provider_factory.create_agent(model_def)
        except Exception as e:
            raise ProcessorError(
                f"Failed to create LLM agent for model '{model_id}': {e} - "
                f"Check provider_auth configuration and API keys"
            ) from e

        # Build comprehensive prompt for scenario generation
        generation_prompt = f"""Generate {prompt_config["count"]} conversational evaluation scenarios based on this description:

{prompt_config["prompt"]}

For each scenario, provide:
- id: Unique scenario identifier (e.g., "scenario-1", "scenario-2")
- user_goal: Clear, actionable description of what the simulated user is trying to accomplish
- context: Background context for the conversation (optional, can be null if not needed)
- dialogue_guidance: Optional guidance for turn generation behavior with these fields:
  * tone_preference: Desired tone (e.g., "professional", "casual", "frustrated", "helpful")
  * escalation_strategy: How user should escalate if goal not met (e.g., "politely insist", "ask for supervisor", "express frustration")
  * factual_constraints: Optional list of facts the simulated user knows and may reference

Return ONLY a JSON array of scenarios. Each scenario should be a valid JSON object. Do not include any explanations or additional text outside the JSON."""

        self.logger.info(f"Generating {prompt_config['count']} scenarios using model: {model_id}")

        # Call LLM with temperature=0 for deterministic output
        try:
            result = await provider_factory.call_agent(agent, generation_prompt)
            llm_output = result.output.strip()

            # Parse LLM response as JSON
            scenarios = self._parse_llm_response(llm_output)

            self.logger.info(f"Generated {len(scenarios)} scenarios using LLM")
            return scenarios

        except Exception as e:
            raise ProcessorError(
                f"LLM scenario generation failed: {e} - "
                f"Check model configuration, API keys, and prompt format"
            ) from e

    def _parse_llm_response(self, llm_output: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response into structured scenario objects.

        Args:
            llm_output: Raw LLM response string

        Returns:
            List of parsed scenario dictionaries

        Raises:
            ProcessorError: If parsing fails or response is invalid
        """
        try:
            # Extract JSON from LLM response
            scenarios = self._extract_json_from_response(llm_output)

            # Validate and clean each scenario
            validated_scenarios = []
            for i, scenario in enumerate(scenarios):
                if self._validate_scenario(scenario):
                    validated_scenarios.append(scenario)
                else:
                    keys = list(scenario.keys()) if isinstance(scenario, dict) else type(scenario).__name__
                    self.logger.warning(f"Skipping invalid scenario {i + 1} (keys: {keys})")

            if not validated_scenarios:
                raise ValueError("No valid scenarios found in LLM response")

            return validated_scenarios

        except json.JSONDecodeError as e:
            raise ProcessorError(
                f"Failed to parse LLM response as JSON: {e} - LLM output: {llm_output[:200]}..."
            ) from e
        except Exception as e:
            raise ProcessorError(
                f"Failed to parse LLM response: {e} - Check prompt format and LLM output structure"
            ) from e

    def _extract_json_from_response(self, llm_output: str) -> List[Dict[str, Any]]:
        """
        Extract JSON array from LLM response string.

        Args:
            llm_output: Raw LLM response string

        Returns:
            List of scenario dictionaries

        Raises:
            ValueError: If JSON cannot be extracted or is invalid
        """
        # Try to parse as JSON array directly
        if llm_output.startswith("[") or llm_output.startswith("{"):
            scenarios = json.loads(llm_output)
        else:
            # Try to extract JSON from response (handle markdown code blocks)
            scenarios = self._extract_json_with_patterns(llm_output)

        # Ensure it's a list
        return cast(List[Dict[str, Any]], scenarios)

    def _extract_json_with_patterns(self, llm_output: str) -> List[Dict[str, Any]]:
        """
        Extract JSON from LLM response using regex patterns.

        Args:
            llm_output: Raw LLM response string

        Returns:
            List of scenario dictionaries
        """
        # Look for JSON in code blocks
        json_match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", llm_output)
        if json_match:
            return cast(List[Dict[str, Any]], json.loads(json_match.group(1)))

        # Look for JSON array in the text
        json_match = re.search(r"(\[[\s\S]*?\])", llm_output)
        if json_match:
            return cast(List[Dict[str, Any]], json.loads(json_match.group(1)))

        # Try parsing the whole response
        return cast(List[Dict[str, Any]], json.loads(llm_output))

    def _validate_scenario(self, scenario: Dict[str, Any]) -> bool:
        """
        Validate scenario has required fields.

        Args:
            scenario: Scenario dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Required fields
            if "id" not in scenario or not scenario["id"]:
                return False

            if "user_goal" not in scenario or not scenario["user_goal"]:
                return False

            # Optional fields - if present, validate structure
            if "dialogue_guidance" in scenario and scenario["dialogue_guidance"]:
                guidance = scenario["dialogue_guidance"]
                if not isinstance(guidance, dict):
                    return False

            return True

        except Exception:
            return False

    def _save_scenarios(self, scenarios: List[Dict[str, Any]], context: RunContext) -> Path:
        """
        Save scenarios to JSONL file.

        Args:
            scenarios: List of scenario dictionaries
            context: RunContext with output directory

        Returns:
            Path to saved scenarios.jsonl file

        Raises:
            ProcessorError: If file writing fails
        """
        # Determine output directory
        output_dir = getattr(context, "output_directory", Path("."))
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        # Ensure directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save scenarios as JSONL
        scenarios_file = output_dir / "scenarios.jsonl"

        try:
            with scenarios_file.open("w", encoding="utf-8") as f:
                for scenario in scenarios:
                    f.write(json.dumps(scenario, ensure_ascii=False) + "\n")

            self.logger.info(f"Saved {len(scenarios)} scenarios to {scenarios_file}")
            return scenarios_file

        except Exception as e:
            raise ProcessorError(
                f"Failed to save scenarios to {scenarios_file}: {e} - "
                f"Check disk space and directory permissions"
            ) from e
