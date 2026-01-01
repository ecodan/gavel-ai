# Gavel-AI

Open-source, provider-agnostic AI evaluation framework for testing LLM applications locally and in production.

## Features

- **Provider Agnostic:** Works with Claude, GPT, Gemini, Ollama via Pydantic-AI
- **Multiple Workflows:** OneShot, Conversational (v2+), Autotune (v3+)
- **Built-in Judges:** DeepEval integration + custom GEval support
- **Local First:** All data stays on your machine
- **OpenTelemetry:** Native observability instrumentation
- **Git-Friendly:** Human-readable JSON/JSONL artifacts

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Configure API Keys

Create a `.env` file with your API keys:

```bash
cp .env.example .env
# Edit .env and add your keys
```

Gavel automatically loads `.env` on startup. See [SETUP.md](SETUP.md) for complete configuration guide.

### 3. Create Your First Evaluation

```bash
gavel oneshot create --eval my_first_eval
cd .gavel/evaluations/my_first_eval
```

Edit the config files:
- `config/agents.json` - Define models and agents
- `data/scenarios.json` - Add test scenarios
- `config/eval_config.json` - Configure judges

### 4. Run Evaluation

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
pytest                    # Run all tests
pytest tests/unit         # Unit tests only
pytest tests/integration  # Integration tests only
```

### Code Quality

```bash
black src/                # Format code
ruff check src/           # Lint code
mypy src/                 # Type check
```

### Pre-commit Hooks

```bash
pre-commit install        # Install hooks
pre-commit run --all-files  # Run all hooks
```

## Architecture

Gavel follows a clean architecture pattern:

- **Workflows:** OneShot, Conversational, Autotune
- **Processors:** PromptInputProcessor, ClosedBoxInputProcessor, ScenarioProcessor
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

## License

[Add license information]

## Contributing

[Add contributing guidelines]

## Support

- Issues: [GitHub Issues](https://github.com/your-org/gavel-ai/issues)
- Documentation: [docs/](docs/)
