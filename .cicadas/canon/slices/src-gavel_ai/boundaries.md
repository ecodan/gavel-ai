## Input Boundaries

- **Config Files**: `config/agents.json`, `config/eval_config.json`, `config/async_config.json`, and judge-specific JSON files.
- **Data Files**: `data/scenarios.json` or `data/scenarios.csv`.
- **System Environment**: API keys (e.g., `ANTHROPIC_API_KEY`) loaded via `.env` or system environment variables.
- **LLM Providers**: Responses from Claude, GPT, Gemini, and Ollama via the Pydantic-AI wrapper.

## Output Boundaries

- **Run Artifacts**:
  - `results_raw.jsonl`: Immutable log of processor outputs.
  - `results_judged.jsonl`: Aggregate result with judge scores and reasoning.
  - `telemetry.jsonl`: Flat log of OpenTelemetry spans.
  - `gavel.log`: Detailed execution and debug logging.
- **Reporting**:
  - `report.html`: Jinja2-rendered HTML dashboard.
- **Metric Surface**:
  - `run_metadata.json`: High-level summary of timing, token usage, and error rates.

## Public Interface

- **CLI Shell**: The `gavel` command hierarchy (built on Typer/Click).
- **Core Models**: Pydantic models in `gavel_ai.core.models` used by plugins and extensions.
