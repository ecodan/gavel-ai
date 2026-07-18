# Gavel-AI

Open-source, provider-agnostic AI evaluation framework for testing LLM applications locally and in production.

## Features

- **Provider Agnostic:** Works with Claude, GPT, Gemini, Ollama via Pydantic-AI
- **Multiple Workflows:** OneShot, Conversational, Autotune (automated iterative prompt optimization)
- **Built-in Judges:** 11 DeepEval judge types (GEval, toxicity, conversational, faithfulness, and more) + deterministic GT-comparison metrics
- **Local First:** All data stays on your machine
- **OpenTelemetry:** Native observability instrumentation
- **Git-Friendly:** Human-readable JSON/JSONL artifacts

## Quick Start

### 1. Install

```bash
# Development (editable)
pip install -e .

# As a library in another project
pip install gavel-ai
# or with uv:
uv add /path/to/gavel-ai
```

### 2. Configure API Keys

Create a `.env` file with your API keys:

```bash
cp .env.example .env
# Edit .env and add your keys
```

Gavel automatically loads `.env` on startup. See [SETUP.md](SETUP.md) for complete configuration guide.

### 3. Initialize Your Project

```bash
gavel init                    # Uses .gavel/evaluations (default)
gavel init --eval-root ./evals  # Or specify a custom root
```

### 4. Create Your First Evaluation

```bash
gavel oneshot create --eval my_first_eval
cd .gavel/evaluations/my_first_eval
```

Edit the config files:
- `config/agents.json` - Define models and agents
- `data/scenarios.json` - Add test scenarios
- `config/eval_config.json` - Configure judges

### 5. Run Evaluation

```bash
gavel oneshot run --eval my_first_eval
```

Results are saved in `.gavel/evaluations/my_first_eval/runs/<timestamp>/`

## Project Structure

```
gavel-ai/
├── src/gavel_ai/          # Source code
│   ├── cli/               # CLI commands
│   ├── core/              # Core abstractions
│   ├── processors/        # Execution processors
│   ├── judges/            # Evaluation judges
│   ├── storage/           # Artifact storage
│   └── reporters/         # Report generation
├── tests/                 # Unit and integration tests
├── docs/                  # Documentation
├── .env.example          # Environment variable template
└── SETUP.md              # Complete setup guide
```

## Documentation

- **[SETUP.md](SETUP.md)** - Complete API key configuration and setup
- **[docs/quickstart/](docs/quickstart/)** - Step-by-step tutorials
- **[docs/cli-reference/](docs/cli-reference/)** - CLI command reference
- **[docs/examples/](docs/examples/)** - Example evaluations

## Development

### Running Tests

```bash
uv run pytest             # Run all tests
uv run pytest -m unit     # Unit tests only
uv run pytest -m integration  # Integration tests only
```

### Code Quality

```bash
uv run black src/         # Format code
uv run ruff check src/    # Lint code
uv run mypy src/          # Type check
```

### Pre-commit Hooks

```bash
pre-commit install        # Install hooks
pre-commit run --all-files  # Run all hooks
```

## Architecture

Gavel follows a clean architecture pattern:

- **Workflows:** OneShot, Conversational, Autotune
- **Processors:** PromptInputProcessor (local), ExternalHttpProcessor and ScriptInputProcessor (closed-box/external SUT via `test_subject_type: "external"`, config-driven inside `oneshot`)
- **Judges:** DeepEval judges + custom GEval
- **Storage:** Filesystem-based (database/S3 future)
- **Reporters:** Jinja2 templates (HTML, Markdown)

See [architecture.md](_bmad-output/planning-artifacts/architecture.md) for details.

## Environment Variables

Gavel automatically loads `.env` files using `python-dotenv`. Configuration files support `{{VAR_NAME}}` substitution:

```json
{
  "provider_auth": {
    "api_key": "{{ANTHROPIC_API_KEY}}"
  }
}
```

**Supported Variables:**
- `ANTHROPIC_API_KEY` - Claude models
- `OPENAI_API_KEY` - GPT models
- `GOOGLE_API_KEY` - Gemini models
- `OLLAMA_BASE_URL` - Local Ollama instance
- `GAVEL_EVAL_ROOT` - Override the default evaluations root directory

## License

[Add license information]

## Contributing

[Add contributing guidelines]

## Support

- Issues: [GitHub Issues](https://github.com/your-org/gavel-ai/issues)
- Documentation: [docs/](docs/)
