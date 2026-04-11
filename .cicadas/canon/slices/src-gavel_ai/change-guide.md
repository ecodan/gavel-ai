## Change Guide

### Adding a New Workflow (Processor)

1. Create a new subclass of `InputProcessor` in `src/gavel_ai/processors/`.
2. Implement the `process()` method following the pattern in `prompt_processor.py`.
3. Register the new processor in `src/gavel_ai/processors/factory.py` (if using a factory pattern).
4. Add a corresponding command to the Typer app in `src/gavel_ai/cli/workflows.py`.
5. Update `tests/integration/test_<workflow>_execution.py`.

### Adding a New Judge

1. Implement the `Judge` base class in `src/gavel_ai/judges/base.py`.
2. If leveraging DeepEval, wrap their judge in a Gavel-compatible class in `src/gavel_ai/judges/deepeval_judge.py`.
3. Register the judge with a unique `deepeval.<name>` or `custom.<name>` alias in `src/gavel_ai/judges/judge_registry.py`.

### Modifying Artifact Schema

1. Update the Pydantic models in `src/gavel_ai/core/models.py`.
2. Update the `RunContext` save/load methods in `src/gavel_ai/storage/run_context.py` to handle the new fields.
3. Ensure the `Reporters` can render the new data by updating the templates in `src/gavel_ai/reporters/templates/`.

### Observability

Every new significant service or asynchronous loop should be wrapped in a New Span:
```python
from gavel_ai.telemetry import get_tracer
tracer = get_tracer(__name__)

with tracer.start_as_current_span("my.new.operation") as span:
    # operation logic
    span.set_attribute("data.key", value)
```
