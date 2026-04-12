---
summary: "Ordered task checklist for 5 phases: Input subclassing, template rendering, processor simplification, integration testing"
phase: "tasks"
when_to_load:
  - "During daily coding"
  - "To track completion"
depends_on:
  - "approach.md"
modules: []
---

# Implementation Tasks

## Phase 1: Input Subclassing (feat/input-subclass)

### 1.1 Create Input Subclasses
- [ ] Update `src/gavel_ai/models/runtime.py`:
  - [ ] Create `PromptInput` with `user: str`, `system: Optional[str]`
  - [ ] Create `RemoteSystemInput` with endpoint, method, headers, body, auth
  - [ ] Create `ConversationalInput` (future-proofing)
  - [ ] Keep `Input` as base class; document subclass contract
- [ ] Add Pydantic validation and docstrings
- [ ] Run `mypy src/gavel_ai/models/` — verify no errors

### 1.2 Unit Tests for Input Subclasses
- [ ] Create `tests/unit/models/test_input_types.py`
  - [ ] Test PromptInput creation with user + system
  - [ ] Test PromptInput with system=None
  - [ ] Test RemoteSystemInput with all fields
  - [ ] Test ConversationalInput with turns list
  - [ ] Test validation (required fields, types)
- [ ] Run `pytest -m unit tests/unit/models/test_input_types.py` — all green

### 1.3 Backward Compatibility
- [ ] Check if existing code instantiates `Input` directly
- [ ] Create factory or alias if needed
- [ ] Document migration path in docstring

---

## Phase 2: ScenarioProcessorStep Template Rendering (feat/scenario-template-rendering)

### 2.1 Add Template Rendering to ScenarioProcessorStep
- [ ] Update `src/gavel_ai/core/steps/scenario_processor.py`:
  - [ ] Add `_render_template(template: str, variables: Dict[str, Any]) -> str` method
  - [ ] Use Jinja2 `Template` to render with `input=variables`
  - [ ] Handle rendering errors: raise `ProcessorError` with context
  - [ ] Load template once per test_subject via `context.get_prompt(test_subject)`
  - [ ] Create `PromptInput` or `RemoteSystemInput` based on processor_type
  - [ ] Preserve scenario_input in metadata dict

- [ ] Update `_convert_scenarios()` method:
  - [ ] Load prompt template based on test_subject_config.prompt_name
  - [ ] For each scenario:
    - [ ] Render template with scenario.input as variables
    - [ ] Create `PromptInput(user=rendered_prompt, system=None, metadata={...})`
    - [ ] Store `scenario_input` in metadata for debugging
    - [ ] Store `template` name in metadata
  - [ ] Return `List[PromptInput]` instead of `List[Input]`

### 2.2 Error Handling
- [ ] Handle missing template: raise `ConfigError` with helpful message
- [ ] Handle rendering failure: raise `ProcessorError` with template context
- [ ] Add logging for template loading and rendering

### 2.3 Unit Tests for Template Rendering
- [ ] Create `tests/unit/core/steps/test_scenario_processor.py`
  - [ ] Test template rendering with dict variables
  - [ ] Test template rendering with string variables
  - [ ] Test missing template error
  - [ ] Test rendering failure error
  - [ ] Test PromptInput creation with metadata
- [ ] Run tests — all green

### 2.4 Integration Test with media-lens-headline-extraction
- [ ] Load `.gavel/evaluations/media-lens-headline-extraction/` config
- [ ] Instantiate ScenarioProcessorStep
- [ ] Execute step on sample scenarios
- [ ] Verify PromptInput.user contains rendered template (not stringified dict)
- [ ] Log rendered prompts for manual inspection

---

## Phase 3: PromptInputProcessor Simplification (feat/prompt-processor-simple)

### 3.1 Update PromptInputProcessor
- [ ] Update `src/gavel_ai/processors/prompt_processor.py`:
  - [ ] Change signature: `async def process(self, inputs: List[PromptInput]) -> ProcessorResult`
  - [ ] Construct messages from PromptInput:
    ```python
    messages = []
    if input_item.system:
        messages.append({"role": "system", "content": input_item.system})
    messages.append({"role": "user", "content": input_item.user})
    ```
  - [ ] Call LLM with messages (via `_call_llm()`)
  - [ ] Aggregate outputs and metadata
  - [ ] Keep retry logic with `retry_with_backoff()`

- [ ] Remove template loading stub (lines 117–119)
- [ ] Simplify `_call_llm()` signature to accept messages

### 3.2 Unit Tests for PromptInputProcessor
- [ ] Create `tests/unit/processors/test_prompt_processor.py`
  - [ ] Mock LLM provider
  - [ ] Test process() with PromptInput
  - [ ] Test message construction (user only, user + system)
  - [ ] Test LLM call with proper message format
  - [ ] Test retry logic
  - [ ] Test batch processing
  - [ ] Test metadata aggregation
- [ ] Run `pytest -m unit tests/unit/processors/test_prompt_processor.py` — all green

---

## Phase 4: ClosedBoxInputProcessor Update (feat/closedbox-remote-input)

### 4.1 Update ClosedBoxInputProcessor
- [ ] Update `src/gavel_ai/processors/closedbox_processor.py`:
  - [ ] Change signature: `async def process(self, inputs: List[RemoteSystemInput]) -> ProcessorResult`
  - [ ] Build HTTP requests from RemoteSystemInput:
    ```python
    request = {
        "method": input_item.method,
        "url": input_item.endpoint,
        "headers": input_item.headers,
        "json": input_item.body,
        "auth": input_item.auth
    }
    ```
  - [ ] Call HTTP client with request
  - [ ] Handle responses and errors

### 4.2 Unit Tests for ClosedBoxInputProcessor
- [ ] Create `tests/unit/processors/test_closedbox_processor.py`
  - [ ] Mock HTTP client
  - [ ] Test process() with RemoteSystemInput
  - [ ] Test request construction
  - [ ] Test response parsing
  - [ ] Test error handling
- [ ] Run `pytest -m unit tests/unit/processors/test_closedbox_processor.py` — all green

---

## Phase 5: Integration Testing (feat/integration-tests)

### 5.1 End-to-End Test: media-lens-headline-extraction
- [ ] Create `tests/integration/test_processor_chain_e2e.py`
  - [ ] Load media-lens-headline-extraction evaluation
  - [ ] Create LocalRunContext with evaluation
  - [ ] Execute ValidatorStep
  - [ ] Execute ScenarioProcessorStep
  - [ ] Verify:
    - [ ] PromptInput objects are created correctly
    - [ ] No stringified dicts in PromptInput.user
    - [ ] Template is loaded and rendered
  - [ ] Verify ProcessorResult output is JSON
  - [ ] Verify output contains "stories" key (matches template expectations)

### 5.2 Judge Validation
- [ ] Create `tests/integration/test_judge_validation.py`
  - [ ] Execute JudgeRunnerStep on processor results
  - [ ] Verify judge receives correct scenario (via scenario_id FK lookup)
  - [ ] Verify judge scores successfully (no schema errors)
  - [ ] Verify judge output is stored correctly

### 5.3 Regression Testing
- [ ] Run full test suite: `pytest -m unit -m integration` — all pass
- [ ] Run specific evaluation tests if they exist
- [ ] Type check: `mypy src/gavel_ai/` — no errors
- [ ] Lint: `ruff check src/gavel_ai/` — no errors
- [ ] Format: `black src/gavel_ai/` — check formatting

### 5.4 Manual Validation
- [ ] Run actual evaluation:
  ```bash
  gavel oneshot run --eval media-lens-headline-extraction
  gavel oneshot judge --eval media-lens-headline-extraction
  gavel oneshot report --eval media-lens-headline-extraction
  ```
- [ ] Inspect results_raw.jsonl — verify processor output is JSON with "stories"
- [ ] Inspect results_judged.jsonl — verify judge scores are populated (not null/error)
- [ ] Review report.html — verify scores displayed correctly

---

## Completion Checklist

- [ ] All unit tests passing (Phase 1–4)
- [ ] All integration tests passing (Phase 5)
- [ ] media-lens-headline-extraction evaluation completes successfully
- [ ] Judge scores are correct and stored
- [ ] No type errors: `mypy src/gavel_ai/`
- [ ] No lint errors: `ruff check src/gavel_ai/`
- [ ] Code formatted: `black src/gavel_ai/`
- [ ] PR created and merged (if using PR workflow)
- [ ] Canon synthesized and updated
