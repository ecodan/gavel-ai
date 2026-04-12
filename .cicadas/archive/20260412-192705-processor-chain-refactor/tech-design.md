---
summary: "Input subclassing (PromptInput, RemoteSystemInput) + template rendering in ScenarioProcessorStep + processor simplification"
phase: "tech"
when_to_load:
  - "During Phase 1–4 implementation"
depends_on:
  - "prd.md"
modules:
  - "src/gavel_ai/models/runtime.py"
  - "src/gavel_ai/core/steps/scenario_processor.py"
  - "src/gavel_ai/processors/prompt_processor.py"
  - "src/gavel_ai/processors/closedbox_processor.py"
---

# Technical Design: Processor Chain Refactor

## Architecture: Input Subclass Hierarchy

Replace generic `Input(id, text, metadata)` with specialized subtypes:

### PromptInput (for LLM processors)
```python
class PromptInput(Input):
    """Input for PromptInputProcessor.
    
    Represents a prepared prompt ready for LLM consumption.
    """
    user: str  # User-facing prompt message (pre-rendered)
    system: Optional[str] = None  # System instructions (optional)
```

### RemoteSystemInput (for external API processors)
```python
class RemoteSystemInput(Input):
    """Input for ClosedBoxInputProcessor.
    
    Represents an external API call.
    """
    endpoint: str
    method: str  # GET, POST, etc.
    headers: Dict[str, str]
    body: Dict[str, Any]
    auth: Optional[Dict[str, str]] = None
```

### ConversationalInput (for future multi-turn)
```python
class ConversationalInput(Input):
    """Input for conversational processors.
    
    Represents conversation turns with roles.
    """
    turns: List[Dict[str, str]]  # [{"role": "user", "content": "..."}]
    system: Optional[str] = None
```

## Data Flow: Template Rendering at Boundary

### Before (Broken)
```
Scenario (input: {site, html})
  ↓ ScenarioProcessorStep
Input (text: "{'site': '...', 'html': '...'}")  ← BUG: Stringified
  ↓ PromptInputProcessor
LLM receives stringified dict  ← Ignores template, produces generic output
```

### After (Fixed)
```
Scenario (input: {site, html})
  ↓ ScenarioProcessorStep.execute()
  ├─ Load template: context.get_prompt("default:v1")
  ├─ Render: template.render(input={site, html})
  └─ Create PromptInput(user="<rendered prompt>", system=None, metadata={...})
    ↓ PromptInputProcessor.process()
    ├─ Construct messages from PromptInput
    └─ Call LLM with rendered prompt
      ↓ LLM output: JSON with "stories" key ✓
```

## File Changes Summary

| File | Change | Impact |
|------|--------|--------|
| `src/gavel_ai/models/runtime.py` | Add Input subclasses | Medium (new types, backward compat via base class) |
| `src/gavel_ai/core/steps/scenario_processor.py` | Add template rendering | Medium (new `_render_template()` method) |
| `src/gavel_ai/processors/prompt_processor.py` | Simplify, accept PromptInput | Low (remove stub, accept new type) |
| `src/gavel_ai/processors/closedbox_processor.py` | Accept RemoteSystemInput | Medium (refactor) |

## Key Design Decisions

1. **Template rendering in ScenarioProcessorStep**: Data boundary operation, keeps processor simple
2. **Subclassing over branching**: Type hints make contracts explicit, better IDE support
3. **Backward compatibility**: Keep `Input` as base class or factory; processors declare input types
4. **Metadata preservation**: Store `scenario_input` in metadata for debugging; judges join original scenario by scenario_id
