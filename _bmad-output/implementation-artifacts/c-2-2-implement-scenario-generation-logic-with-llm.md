# Story C-2.2: Implement Scenario Generation Logic with LLM

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want GenerateStep to invoke LLM to generate scenarios from a prompt,
so that users can describe test needs and get scenarios automatically.

## Acceptance Criteria

1. Given prompts/generate_scenarios.toml loaded with scenario generation task, when LLM invoked (via Executor) with temperature=0, then LLM generates N scenarios based on prompt description
2. Given LLM generates scenarios, when output parsed, then each scenario has: id (auto-generated or from LLM), user_goal (from LLM), context (from LLM), dialogue_guidance (from LLM, optional)
3. Given dialogue_guidance included, when examined, then it contains tone, escalation_strategy, factual_constraints as appropriate for scenario
4. Given same prompt run twice with temperature=0, when scenarios generated, then identical scenario set produced (deterministic)
5. Given scenarios generated, when written to scenarios.jsonl (JSONL format), then each line is valid JSON; one scenario per line; no nesting; ready for ConversationalProcessingStep

## Tasks / Subtasks

- [x] Task 1: Implement LLM-based scenario generation (AC: 1, 2)
  - [x] Subtask 1.1: Configure LLM agent with temperature=0 for deterministic output
  - [x] Subtask 1.2: Design prompt template for scenario generation
  - [x] Subtask 1.3: Parse LLM response into structured scenario objects
- [x] Task 2: Implement dialogue guidance generation (AC: 3)
  - [x] Subtask 2.1: Generate tone recommendations for scenarios
  - [x] Subtask 2.2: Create escalation strategies if applicable
  - [x] Subtask 2.3: Add factual constraints where needed
- [x] Task 3: Ensure deterministic generation (AC: 4)
  - [x] Subtask 3.1: Set temperature=0 for LLM calls
  - [x] Subtask 3.2: Use consistent seed or deterministic parameters
  - [x] Subtask 3.3: Validate identical outputs for same input
- [x] Task 4: Implement JSONL output formatting (AC: 5)
  - [x] Subtask 4.1: Convert scenario objects to valid JSON
  - [x] Subtask 4.2: Write one scenario per line to scenarios.jsonl
  - [x] Subtask 4.3: Validate JSONL format before writing

## Dev Notes

- Use Executor pattern consistent with other processor components
- Temperature=0 ensures deterministic scenario generation (NFR-C-R4)
- JSONL output format aligns with existing scenario loading patterns
- Generated scenarios must be compatible with ConversationalProcessingStep input requirements

### Project Structure Notes

- GenerateStep implementation in: src/gavel_ai/processors/
- LLM agent creation via existing ProviderFactory
- JSONL output to: data/scenarios.jsonl (consistent with CLI scaffolding)
- Error handling for LLM failures and parsing errors

### References

- [Source: epics-conversational-eval.md#Story-C2.2](epics-conversational-eval.md#Story-C2.2)
- [Source: architecture.md#LLM-Integration](architecture.md#LLM-Integration)
- [Source: architecture.md#JSONL-Format](architecture.md#JSONL-Format)
- Related Requirements: FR-C1.2, NFR-C-R4 (Determinism)

## Dev Agent Record

### Agent Model Used

Claude-4.5-Sonnet-latest

### Debug Log References

### Completion Notes List

**All Tasks Complete (2026-01-18):**

**Task 1 - LLM-based Scenario Generation (AC: 1, 2):**
- ✅ Integrated ProviderFactory to create LLM agents with temperature=0 for deterministic output
- ✅ Built comprehensive prompt template for scenario generation
- ✅ Implemented robust LLM response parsing with JSON extraction (handles markdown code blocks, regex patterns)
- ✅ Added error handling for LLM failures and parsing errors
- ✅ Used structured scenario validation

**Task 2 - Dialogue Guidance Generation (AC: 3):**
- ✅ Prompt template instructs LLM to generate dialogue_guidance with proper structure
- ✅ Handles tone_preference, escalation_strategy, and factual_constraints fields
- ✅ Supports optional dialogue_guidance (can be null in scenarios)

**Task 3 - Deterministic Generation (AC: 4):**
- ✅ Sets temperature=0 in model_parameters for all LLM calls
- ✅ Ensures consistent deterministic output for same input
- ✅ Uses ProviderFactory pattern consistent with other components

**Task 4 - JSONL Output Formatting (AC: 5):**
- ✅ Outputs scenarios.jsonl with one JSON object per line
- ✅ Uses json.dumps() with ensure_ascii=False for proper encoding
- ✅ Validated JSON format before writing
- ✅ Compatible with ConversationalProcessingStep input requirements

**Implementation Details:**
- File: `src/gavel_ai/core/steps/generate_step.py` (completely rewritten with LLM integration)
- Key methods: `_generate_scenarios()`, `_parse_llm_response()`, `_extract_json_from_response()`, `_extract_json_with_patterns()`
- ProviderFactory integration: Creates agents with temperature=0, calls LLM, processes responses
- Error handling: Comprehensive with ProcessorError for LLM and parsing failures
- Code quality: Refactored complex parsing into smaller methods, passes ruff linting
- JSON parsing: Robust extraction supporting multiple LLM response formats

**Architecture Compliance:**
- Follows ProviderFactory pattern used by PromptInputProcessor and other components
- Uses same telemetry pattern as other steps
- Integrates with existing agents.json configuration system
- Maintains async/await pattern throughout

### File List

**Modified Files:**
- src/gavel_ai/core/steps/generate_step.py (Complete LLM integration implementation)
- _bmad-output/implementation-artifacts/c-2-2-implement-scenario-generation-logic-with-llm.md (story status, completion notes, change log)

**Test Files:**
- tests/unit/core/steps/test_generate_step_llm_integration.py (5 comprehensive tests covering LLM integration, parsing, deterministic generation, JSONL output)
- tests/unit/core/steps/test_generate_step.py (existing tests continue to pass)
