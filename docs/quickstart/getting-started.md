# Getting Started with Gavel-AI

This guide walks you through creating and running your first AI evaluation with Gavel.

## Prerequisites

- Python 3.10+ (3.13+ recommended)
- API key for Claude, GPT, or Ollama running locally

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/gavel-ai.git
cd gavel-ai

# Install dependencies
pip install -e .
```

## Step 1: Configure API Keys

Gavel automatically loads environment variables from a `.env` file.

### Create `.env` file

```bash
cp .env.example .env
```

### Add your API key

Edit `.env`:

```bash
# For Claude models
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here

# For GPT models (optional)
OPENAI_API_KEY=sk-your-actual-key-here

# For local Ollama (optional)
OLLAMA_BASE_URL=http://localhost:11434
```

**Important:** `.env` is in `.gitignore` - your keys stay private.

## Step 2: Create an Evaluation

```bash
gavel oneshot create --eval my_eval
```

This creates:

```
.gavel/evaluations/my_eval/
├── config/
│   ├── agents.json        # Model and agent definitions
│   ├── eval_config.json   # Evaluation settings
│   ├── async_config.json  # Concurrency settings
│   └── judges/            # Custom judge configs
├── data/
│   ├── scenarios.json     # Test scenarios
│   └── scenarios.csv      # Alternative CSV format
├── prompts/
│   └── default.toml       # Prompt templates
└── runs/                  # Evaluation results (auto-created)
```

## Step 3: Configure Your Evaluation

### Edit `config/agents.json`

The scaffolding already includes `{{ANTHROPIC_API_KEY}}` environment variable substitution:

```json
{
  "_models": {
    "claude-standard": {
      "model_provider": "anthropic",
      "model_family": "claude",
      "model_version": "claude-sonnet-4-5-latest",
      "model_parameters": {
        "temperature": 0.7,
        "max_tokens": 4096
      },
      "provider_auth": {
        "api_key": "{{ANTHROPIC_API_KEY}}"
      }
    }
  },
  "subject_agent": {
    "model_id": "claude-standard",
    "prompt": "assistant:v1"
  }
}
```

### Edit `data/scenarios.json`

Add your test scenarios:

```json
{
  "scenarios": [
    {
      "id": "greeting",
      "input": {
        "message": "Hello! How are you?"
      },
      "expected_behavior": "Friendly greeting response"
    },
    {
      "id": "factual_query",
      "input": {
        "message": "What is the capital of France?"
      },
      "expected_behavior": "Correct factual answer"
    }
  ]
}
```

### Edit `config/eval_config.json`

Configure evaluation judges:

```json
{
  "judges": [
    {
      "id": "relevancy",
      "deepeval_name": "deepeval.answer_relevancy",
      "config": {
        "threshold": 0.7
      }
    }
  ]
}
```

## Step 4: Run Your Evaluation

```bash
gavel oneshot run --eval my_eval
```

Gavel will:
1. Automatically load your `.env` file
2. Load all configuration files
3. Execute scenarios against your agent
4. Run judges to evaluate outputs
5. Generate a report

## Step 5: View Results

Results are saved in timestamped run directories:

```
.gavel/evaluations/my_eval/runs/run-20260101-093000/
├── manifest.json          # Run metadata
├── config/                # Copy of configs used
├── telemetry.jsonl        # OpenTelemetry traces
├── results.jsonl          # Evaluation results
├── report.html            # Human-readable report
├── run_metadata.json      # Timing and stats
└── gavel.log             # Execution logs
```

### View the report

```bash
open .gavel/evaluations/my_eval/runs/run-*/report.html
```

### List all runs

```bash
gavel oneshot list --eval my_eval
```

## Next Steps

- **Add more scenarios:** Edit `data/scenarios.json`
- **Try different models:** Add to `_models` in `agents.json`
- **Custom judges:** Create GEval judges in `config/judges/`
- **Re-judge results:** `gavel oneshot judge --run <run-id>`
- **Export results:** `gavel export --run <run-id> --format zip`

## Common Issues

### "Environment variable 'ANTHROPIC_API_KEY' not set"

**Fix:** Verify `.env` exists in project root and contains your key.

### "Provider authentication failed"

**Fix:** Check your API key is valid at https://console.anthropic.com

### Can't find evaluation

**Fix:** Run `gavel oneshot create --eval <name>` first, or specify correct eval root.

## More Resources

- [SETUP.md](../../SETUP.md) - Complete setup and configuration guide
- [CLI Reference](../cli-reference/) - All available commands
- [Examples](../examples/) - Example evaluations and use cases
- [Architecture](../../_bmad-output/planning-artifacts/architecture.md) - System design
