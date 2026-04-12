# Processor Chain Bug Fix Plan

**Status**: Planning  
**Priority**: High (blocks all evaluations)  
**Root Cause**: Prompt templates never loaded; LLM receives stringified dict instead of rendered prompt

---

## Executive Summary

The OneShot evaluation pipeline has a critical bug: **prompt templates are never loaded or rendered**. Instead, scenario input is stringified and sent directly to the LLM, causing:

1. LLMs ignore instructions and produce generic summaries
2. Judge evaluations fail (expecting JSON, receiving markdown)
3. All evaluations fail at judge step with schema mismatches

This fix involves:
- **Refactoring Input model** → Subclass into PromptInput, RemoteSystemInput
- **Moving template rendering** → ScenarioProcessorStep (data boundary)
- **Simplifying processors** → Generic, testable, reusable
- **Preserving scenario context** → Join original scenario at judge time by scenario_id

---

## Root Cause Analysis

### Current Flow (Broken)

```
Scenario (scenarios.json)
├── id: "headline-160000-www-bbc-com"
└── input: {"site": "www.bbc.com", "html": "<!DOCTYPE..."}

    ↓ ScenarioProcessorStep._convert_scenarios()

Input
├── id: "headline-160000-www-bbc-com"
├── text: "{'site': 'www.bbc.com', 'html': '...'}"  ← BUG: Stringified input
└── metadata: {}

    ↓ PromptInputProcessor.process()

PromptInputProcessor.process(inputs)
  │
  ├─ prompt = input.text  ← BUG: No template loading
  │           (stringified dict, not template)
  │
  └─ LLM receives malformed prompt
     → Ignores instructions
     → Produces generic markdown analysis
     → Judge fails on schema validation
```

### Why It Happens

1. **PromptInputProcessor is a stub** (`src/gavel_ai/processors/prompt_processor.py:117-119`)
   - Comment: "For now, use the input text directly as the prompt. Real implementation will load template and render with variables"
   - Never implemented

2. **Prompt template never passed to processor**
   - ScenarioProcessorStep knows `test_subject = "default:v1"`
   - Doesn't pass it to PromptInputProcessor
   - Processor has no way to call `context.get_prompt()`

3. **Processor has no access to context**
   - Can't load TOML files
   - Can't call `eval_context.get_prompt()`
   - Violates separation of concerns (processor shouldn't depend on storage)

---

## Solution: Two-Part Fix

### Part 1: Refactor Input Model → Subclass Hierarchy

**Current**: Generic `Input(id, text, metadata)` for all processor types

**New**:
```python
# Base class (core/models/runtime.py)
class Input(BaseModel):
    """Abstract base for processor inputs."""
    id: str
    metadata: Dict[str, Any] = {}

# For LLM-based processors
class PromptInput(Input):
    """Input for PromptInputProcessor.
    
    Represents a prepared prompt ready for LLM consumption.
    System prompt optional; can be merged with user message by processor.
    """
    user: str  # User-facing prompt/message
    system: Optional[str] = None  # System instructions (optional)

# For external API processors
class RemoteSystemInput(Input):
    """Input for ClosedBoxInputProcessor.
    
    Represents an external API call with endpoint, method, body, auth.
    """
    endpoint: str
    method: str  # GET, POST, etc.
    headers: Dict[str, str]
    body: Dict[str, Any]
    auth: Optional[Dict[str, str]] = None

# For future multi-turn conversations
class ConversationalInput(Input):
    """Input for conversational processors.
    
    Represents conversation turns with roles (user/assistant/system).
    """
    turns: List[Dict[str, str]]  # [{"role": "user", "content": "..."}]
    system: Optional[str] = None
```

**Backwards Compatibility**:
- Keep `Input` as abstract base or factory
- Processors declare input type: `PromptInputProcessor(input: List[PromptInput])`
- Type hints make contracts explicit

---

### Part 2: Pre-render Prompts in ScenarioProcessorStep

**Current** (ScenarioProcessorStep):
```python
inputs: List[Input] = [
    Input(
        id=scenario.scenario_id,
        text=scenario.input if isinstance(scenario.input, str) else str(scenario.input),
        metadata=scenario.metadata or {},
    )
    for scenario in scenarios
]
```

**New**:
```python
# Load prompt template once
test_subject = test_subject_config.prompt_name  # "default:v1"
template = context.get_prompt(test_subject)

# Convert scenarios to PromptInput with rendered prompts
inputs: List[PromptInput] = []
for scenario in scenarios:
    # Render template with scenario variables
    rendered_user_prompt = self._render_template(
        template=template,
        variables=scenario.input if isinstance(scenario.input, dict) else {}
    )
    
    inputs.append(PromptInput(
        id=scenario.scenario_id,
        user=rendered_user_prompt,
        system=None,  # Can add later if needed
        metadata={
            "scenario_input": scenario.input,  # Preserve for debugging
            "template": test_subject,
            **scenario.metadata
        }
    ))

def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
    """Render Jinja2 template with scenario variables.
    
    Args:
        template: "You are... {{ input.html }}"
        variables: {"site": "...", "html": "..."}
    
    Returns:
        Rendered prompt with variables substituted
    
    Raises:
        ProcessorError: If required variables missing
    """
    from jinja2 import Template
    try:
        tmpl = Template(template)
        return tmpl.render(input=variables)
    except Exception as e:
        raise ProcessorError(f"Failed to render prompt template: {e}") from e
```

**Benefits**:
- ✅ Template loading happens once per test_subject, not per input
- ✅ ScenarioProcessorStep already has context access
- ✅ Processor becomes simpler (just calls LLM with pre-made prompt)
- ✅ Clean separation: data preparation at boundary, processing in processor

---

### Part 3: Simplify PromptInputProcessor

**Current** (broken stub):
```python
async def process(self, inputs: List[Input]) -> ProcessorResult:
    for input_item in inputs:
        prompt = input_item.text  # ← BUG
        output, metadata = await self._call_llm(prompt)
        # ...
```

**New**:
```python
async def process(self, inputs: List[PromptInput]) -> ProcessorResult:
    """Process LLM prompts.
    
    Args:
        inputs: List[PromptInput] with rendered user/system prompts
    
    Returns:
        ProcessorResult with LLM output
    """
    all_outputs: List[str] = []
    aggregated_metadata: Dict[str, Any] = {
        "total_tokens": 0,
        "total_latency_ms": 0,
        "input_count": len(inputs),
    }
    
    for input_item in inputs:
        # Construct messages from PromptInput
        messages = []
        if input_item.system:
            messages.append({"role": "system", "content": input_item.system})
        messages.append({"role": "user", "content": input_item.user})
        
        # Call LLM
        retry_config = RetryConfig(max_retries=3)
        output, metadata = await retry_with_backoff(
            func=lambda: self._call_llm(messages),
            retry_config=retry_config,
            transient_exceptions=(TimeoutError,),
        )
        
        all_outputs.append(output)
        # Aggregate metadata...
    
    return ProcessorResult(output="\n\n".join(all_outputs), metadata=aggregated_metadata)

async def _call_llm(self, messages: List[Dict]) -> tuple[str, Dict[str, Any]]:
    """Call LLM with structured messages.
    
    Args:
        messages: [{"role": "system|user", "content": "..."}]
    
    Returns:
        (response_text, metadata)
    """
    result = await self.provider_factory.call_agent(self.agent, messages)
    return (result.output, result.metadata)
```

**Benefits**:
- ✅ No template/context awareness needed
- ✅ Generic: works with any rendered prompts
- ✅ Simpler to test: just string → LLM → string
- ✅ Supports system prompts if needed later

---

### Part 4: Judge Integration (No Changes Needed)

Judges already have access to original scenario by `scenario_id`:

```python
# In JudgeRunnerStep.execute()
scenarios_by_id = {s.id: s for s in context.eval_context.scenarios.read()}

for result in processor_results:
    scenario = scenarios_by_id[result.scenario_id]  # FK lookup
    
    # Judge gets both output and original scenario context
    evaluation = await judge.evaluate(
        scenario=scenario,           # Contains GT, exemplars, etc.
        subject_output=result.processor_output
    )
```

No changes needed. Judge can access:
- `scenario.ground_truth` (GT labels)
- `scenario.exemplars` (reference examples)
- `scenario.rubric` (evaluation criteria)
- Plus the processor output to evaluate

---

## Implementation Plan

### Phase 1: Model Refactoring (Input Subclassing)

1. **Create input subclasses** (`src/gavel_ai/models/runtime.py`)
   - `Input` (abstract base or factory)
   - `PromptInput(user, system?, metadata)`
   - `RemoteSystemInput(endpoint, method, headers, body, auth?, metadata)`
   - `ConversationalInput(turns, system?, metadata)` [optional for future]

2. **Update type hints** across codebase
   - `InputProcessor.process(inputs: List[Input])` → type param or subclass type
   - `PromptInputProcessor.process(inputs: List[PromptInput])`
   - `ClosedBoxInputProcessor.process(inputs: List[RemoteSystemInput])`

3. **Tests**: Unit tests for each Input subclass creation and validation

### Phase 2: ScenarioProcessorStep Template Rendering

1. **Add template rendering to ScenarioProcessorStep**
   - Load `context.get_prompt(test_subject)` once per test_subject
   - Add `_render_template()` method using Jinja2
   - Convert scenarios → PromptInput/RemoteSystemInput based on processor_type

2. **Handle errors gracefully**
   - Missing template → ConfigError with helpful message
   - Template rendering failure → ProcessorError with context

3. **Tests**: 
   - Template rendering with various variable formats
   - Missing template error handling
   - Processor type dispatch

### Phase 3: PromptInputProcessor Simplification

1. **Remove template loading logic** (never existed, just remove stub comment)
2. **Update `process()` to accept PromptInput**
   - Handle `user` and `system` fields
   - Call LLM with structured messages
3. **Remove EvalContext dependency**
4. **Tests**: 
   - LLM call with user message
   - LLM call with system + user
   - Retry logic
   - Batch processing

### Phase 4: ClosedBoxInputProcessor Update

1. **Update to accept RemoteSystemInput**
2. **Build HTTP requests from input fields**
   - endpoint, method, headers, body, auth
3. **Tests**: HTTP call construction and execution

### Phase 5: Integration Testing

1. **End-to-end OneShot evaluation**
   - Load scenarios
   - Render prompts
   - Process with LLM
   - Judge results
   - Verify output structure matches expectations

2. **Judge validation**
   - Processor output is JSON with "stories" key
   - Judge scores correctly
   - No schema mismatch errors

---

## Files to Change

| File | Change | Impact |
|------|--------|--------|
| `src/gavel_ai/models/runtime.py` | Add Input subclasses | Medium (new classes, backward compat) |
| `src/gavel_ai/core/steps/scenario_processor.py` | Add template rendering | Medium (logic addition) |
| `src/gavel_ai/processors/prompt_processor.py` | Simplify, remove stub | Low (cleanup) |
| `src/gavel_ai/processors/closedbox_processor.py` | Update for RemoteSystemInput | Medium (refactor) |
| `src/gavel_ai/core/contexts.py` | No changes needed | None |
| `tests/` | Add tests for each phase | Medium (new test files) |

---

## Testing Strategy

### Unit Tests
- **Input subclass validation**: Create each type, validate fields
- **Template rendering**: Jinja2 rendering with various variables
- **Processor execution**: Mock LLM, verify message construction

### Integration Tests
- **Full OneShot flow**: scenarios → outputs → judged results
- **Judge validation**: Verify judge receives correct data
- **Error handling**: Missing templates, rendering failures, LLM errors

### Scenario Tests
- Use existing `media-lens-headline-extraction` evaluation
- Verify:
  - Prompt rendered correctly (not stringified dict)
  - LLM receives proper instructions
  - Output is JSON with "stories" key
  - Judge scores successfully (no schema errors)

---

## Risk & Mitigation

| Risk | Mitigation |
|------|-----------|
| Breaking changes to Input API | Careful type hints, deprecation path if needed |
| Template rendering errors block all scenarios | Fail-fast in ScenarioProcessorStep; surface error early |
| LLM behavior changes with different prompts | Run baseline evaluation after fix; compare outputs |
| Conversational workflows not covered | Design Input hierarchy to support future ConversationalInput |

---

## Success Criteria

- ✅ `PromptInput` created with `user` and optional `system` fields
- ✅ `RemoteSystemInput` created for external API calls
- ✅ ScenarioProcessorStep loads and renders prompt templates
- ✅ PromptInputProcessor receives PromptInput, calls LLM correctly
- ✅ `media-lens-headline-extraction` evaluation runs without errors
- ✅ Processor output is JSON with "stories" key (matches template expectations)
- ✅ Judge evaluations pass schema compliance and quality checks
- ✅ All unit and integration tests pass
- ✅ Backward compatibility maintained (or clear migration path)

---

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| 1. Model refactoring | 2-4 hours | None |
| 2. ScenarioProcessorStep | 2-3 hours | Phase 1 |
| 3. PromptInputProcessor | 1-2 hours | Phase 1, 2 |
| 4. ClosedBoxInputProcessor | 1-2 hours | Phase 1 |
| 5. Integration testing | 2-3 hours | Phases 1-4 |

**Total**: ~10-14 hours (includes testing, debugging, refinement)

---

## Next Steps

1. **Review this plan** with team
2. **Approve Input subclassing design** (open: should ConversationalInput be included?)
3. **Create Cicadas initiative** for this work
4. **Implement Phase 1** (Input subclassing)
5. **Validate with media-lens-headline-extraction** evaluation
