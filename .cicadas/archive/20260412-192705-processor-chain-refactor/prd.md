---
summary: "Fix critical bug where prompt templates are never loaded; LLM receives stringified input instead of rendered prompts. Blocks all evaluations."
phase: "clarify"
when_to_load:
  - "At initiative start"
  - "When evaluating processor chain behavior"
depends_on: []
modules:
  - "src/gavel_ai/models/runtime.py"
  - "src/gavel_ai/core/steps/scenario_processor.py"
  - "src/gavel_ai/processors/prompt_processor.py"
  - "src/gavel_ai/processors/closedbox_processor.py"
---

# Processor Chain Bug Fix

## Problem

The OneShot evaluation pipeline has a **critical, blocking bug**: prompt templates are never loaded or rendered. Instead, the processor receives stringified scenario input and sends it directly to the LLM, causing:

1. **LLMs ignore instructions** and produce generic summaries instead of required JSON
2. **Judge evaluations fail** expecting JSON with "stories" key, receiving markdown
3. **All evaluations fail** at judge step with schema mismatches

**Impact**: No evaluation can complete successfully until this is fixed.

## Root Cause

`PromptInputProcessor.process()` is a stub (lines 117–119):
```python
prompt = input_item.text  # Uses stringified input directly
# Comment: "For now, use the input text directly as the prompt..."
```

It never calls `context.get_prompt()` to load the template from TOML files, and it never calls `eval_context.get_prompt()` because the processor has no access to context.

## Solution: Pre-render Prompts at Data Boundary

Move template rendering from `PromptInputProcessor` to `ScenarioProcessorStep`:

1. **ScenarioProcessorStep** loads the prompt template once per test_subject
2. Renders it with scenario variables using Jinja2
3. Passes rendered prompts to processor via a new `PromptInput` type
4. `PromptInputProcessor` stays simple: just calls LLM with pre-made prompts

This separates concerns cleanly: data preparation at boundaries, processing in processors.

## Success Criteria

- ✅ `PromptInput` created with `user` and optional `system` fields
- ✅ `RemoteSystemInput` created for external API calls
- ✅ ScenarioProcessorStep loads and renders prompt templates
- ✅ PromptInputProcessor receives PromptInput, calls LLM correctly
- ✅ `media-lens-headline-extraction` evaluation runs without errors
- ✅ Processor output is JSON with "stories" key (matches template expectations)
- ✅ Judge evaluations pass schema compliance checks
- ✅ All unit and integration tests pass
