---
summary: "5-phase implementation: Input subclassing → ScenarioProcessorStep template rendering → PromptInputProcessor simplification → ClosedBoxInputProcessor update → Integration testing"
phase: "approach"
when_to_load:
  - "During feature branch planning"
  - "To understand partition boundaries"
depends_on:
  - "prd.md"
  - "tech-design.md"
modules:
  - "src/gavel_ai/models/"
  - "src/gavel_ai/core/steps/"
  - "src/gavel_ai/processors/"
---

# Implementation Approach

## Partitioning Strategy

This initiative is divided into **5 phases**, each a logical feature branch with dependencies:

### Phase 1: Input Subclassing
**Branch**: `feat/input-subclass`  
**Modules**: `src/gavel_ai/models/runtime.py`, tests  
**Duration**: 2–4 hours

Create Input subclass hierarchy:
- `Input` (abstract base)
- `PromptInput(user, system?, metadata)`
- `RemoteSystemInput(endpoint, method, headers, body, auth?, metadata)`
- `ConversationalInput(turns, system?, metadata)` (optional for future)

Deliverables:
- [ ] Input subclasses with Pydantic validation
- [ ] Unit tests for each type
- [ ] Backward compatibility layer

**Blockers**: None  
**Unblocks**: Phases 2, 3, 4

---

### Phase 2: ScenarioProcessorStep Template Rendering
**Branch**: `feat/scenario-template-rendering`  
**Modules**: `src/gavel_ai/core/steps/scenario_processor.py`, tests  
**Duration**: 2–3 hours

Add template loading and rendering:
- Load `context.get_prompt(test_subject)` once per test_subject
- Render Jinja2 templates with scenario variables
- Create PromptInput or RemoteSystemInput based on processor type
- Preserve scenario metadata for debugging

Deliverables:
- [ ] `_render_template()` method with Jinja2
- [ ] Template loading and error handling
- [ ] Variable substitution for PromptInput
- [ ] Integration tests with media-lens-headline-extraction

**Blockers**: Phase 1  
**Unblocks**: Phase 5

---

### Phase 3: PromptInputProcessor Simplification
**Branch**: `feat/prompt-processor-simple`  
**Modules**: `src/gavel_ai/processors/prompt_processor.py`, tests  
**Duration**: 1–2 hours

Simplify processor to accept PromptInput:
- Remove template loading stub
- Handle `user` and `system` fields
- Construct messages for LLM
- Keep retry logic

Deliverables:
- [ ] Updated `process()` signature: `List[PromptInput]`
- [ ] Message construction logic
- [ ] Unit tests for LLM calls
- [ ] Batch processing tests

**Blockers**: Phase 1  
**Unblocks**: Phase 5

---

### Phase 4: ClosedBoxInputProcessor Update
**Branch**: `feat/closedbox-remote-input`  
**Modules**: `src/gavel_ai/processors/closedbox_processor.py`, tests  
**Duration**: 1–2 hours

Update processor to accept RemoteSystemInput:
- Build HTTP requests from input fields
- Handle endpoint, method, headers, body, auth
- Error handling and response parsing

Deliverables:
- [ ] Updated `process()` signature: `List[RemoteSystemInput]`
- [ ] HTTP request construction
- [ ] Unit tests for API calls

**Blockers**: Phase 1  
**Unblocks**: Phase 5

---

### Phase 5: Integration Testing
**Branch**: `feat/integration-tests`  
**Modules**: `tests/`, integration test suite  
**Duration**: 2–3 hours

End-to-end validation:
- Load media-lens-headline-extraction evaluation
- Verify prompt renders correctly (not stringified dict)
- Verify processor output is JSON with "stories" key
- Verify judge evaluation passes schema compliance
- Run full OneShot pipeline

Deliverables:
- [ ] Integration test suite
- [ ] E2E validation of media-lens-headline-extraction
- [ ] Judge schema compliance validation
- [ ] Regression tests for other evaluations

**Blockers**: Phases 2, 3, 4  
**Unblocks**: None

---

## Sequencing & Dependencies

```
Phase 1 (Input subclassing)
  ├─→ Phase 2 (Template rendering)
  │     └─→ Phase 5 (Integration testing)
  ├─→ Phase 3 (PromptInputProcessor)
  │     └─→ Phase 5 (Integration testing)
  └─→ Phase 4 (ClosedBoxInputProcessor)
        └─→ Phase 5 (Integration testing)
```

**Critical path**: 1 → 2 → 5 (11–10 hours)  
**Total effort**: ~10–14 hours (sequential work)

---

## Success Metrics

1. **Code Quality**: All tests pass, no type errors, mypy clean
2. **Functional**: media-lens-headline-extraction evaluation completes without errors
3. **Output Correctness**: Processor output is JSON matching template expectations
4. **Judge Success**: Judge evaluations pass schema validation and quality checks
5. **No Regressions**: Existing tests remain passing
