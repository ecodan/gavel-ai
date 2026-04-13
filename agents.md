# Agent Context: Gavel-AI

**Gavel-AI** is an open-source, provider-agnostic LLM evaluation framework. Benchmark LLM performance across providers (Claude, GPT, Gemini, Ollama) with built-in judges (DeepEval, custom GEval).

## Project Structure

```
gavel-ai/
├── src/gavel_ai/
│   ├── cli/              # Command orchestration (oneshot, conversational, autotune)
│   ├── core/             # Models, step base class, retry logic, exceptions
│   ├── processors/       # OneShot and Conversational execution
│   ├── judges/           # Judge adapters (GEval, DeepEval)
│   ├── reporters/        # Jinja2 report generation (HTML, Markdown)
│   ├── storage/          # Filesystem JSONL persistence
│   ├── providers/        # Pydantic-AI provider factory
│   └── conversational/   # Multi-turn conversation logic and error classification
├── tests/                # Unit and integration tests (marked with @pytest.mark.unit/integration)
├── docs/                 # User documentation
├── .cicadas/             # Cicadas workflow artifacts (see below)
├── CLAUDE.md             # Project conventions, style, CLI commands
├── agents.md             # This file
└── .env.example          # API key template
```

## Authoritative Truth: Canon

The `.cicadas/canon/` directory contains the authoritative documentation, reverse-engineered from code:

- **`summary.md`** — 300–500 token snapshot; start here for dense overview
- **`product-overview.md`** — Purpose, users, workflows
- **`tech-overview.md`** — Architecture, design patterns, module roles
- **`slices/`** — Per-module deep dives (processor, judge, reporter, conversational, storage, provider)
- **`repo.json`** — Machine-readable metadata

For in-flight work, check `.cicadas/active/{initiative}/` for current specs (prd.md, tech-design.md, approach.md, tasks.md).

## Common Development Actions

### Setup
```bash
pip install -e .           # Install in dev mode
cp .env.example .env       # Configure API keys (Anthropic, OpenAI, Google, Ollama)
```

### Code Quality
```bash
black src/                 # Format
ruff check src/           # Lint
mypy src/                 # Type check
```

### Testing
```bash
pytest                          # All tests
pytest -m unit                  # Fast tests only
pytest -m integration           # Real dependencies
pytest tests/path/test.py::test_name  # Specific test
```

### Running Evaluations
```bash
gavel oneshot create --eval my_eval    # Create evaluation
gavel oneshot run --eval my_eval       # Run evaluation
gavel oneshot judge --eval my_eval     # Run judges
gavel oneshot report --eval my_eval    # Generate reports
```

## Key Conventions

- **Type hints**: Mandatory in all function signatures
- **Logging**: Format `"%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"`
- **Snake case**: Code, config, telemetry attributes
- **Test markers**: `@pytest.mark.unit` or `@pytest.mark.integration` (run with `-m`)
- **Immutability**: `results_raw.jsonl` never modified after processor exit
- **OTel instrumentation**: All LLM calls and judge steps emit spans

## For Workflow Guidance

Use the **Cicadas** skill (`/cicadas`) for feature development, bug fixes, and project coordination. Cicadas handles spec drafting, approval, kickoff, branch management, reflect/code-review, and synthesis.

Use the **gavel-skill** (`/gavel-skill`) for evaluation setup, scenario authoring, CLI usage, debugging runs, and interpreting results.

Use the **update-docs** skill (`/update-docs`) before committing to sync `README.md`, `release-notes.md`, `agents.md`, and `CLAUDE.md` with recent changes.

See `.claude/skills/` for complete skill documentation.
