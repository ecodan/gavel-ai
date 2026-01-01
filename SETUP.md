# Gavel-AI Setup Guide

## Quick Start: API Key Configuration

Gavel uses **environment variables** for secure API key management.

### 1. Copy the example environment file

```bash
cp .env.example .env
```

### 2. Add your API keys to `.env`

Edit `.env` and add your actual keys:

```bash
# Required for Claude models
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here

# Required for GPT models
OPENAI_API_KEY=sk-your-actual-openai-key-here

# Optional: for local models
OLLAMA_BASE_URL=http://localhost:11434
```

**Note:** `.env` is already in `.gitignore` - your keys will NOT be committed to git.

### 3. Configure your evaluation

In your evaluation's `agents.json`, reference environment variables using `{{VAR_NAME}}` syntax:

```json
{
  "_models": {
    "claude-standard": {
      "model_provider": "anthropic",
      "model_version": "claude-sonnet-4-5-latest",
      "provider_auth": {
        "api_key": "{{ANTHROPIC_API_KEY}}"
      }
    }
  }
}
```

### 4. Run Gavel (automatic `.env` loading)

Gavel **automatically loads** your `.env` file on startup - no extra steps needed!

```bash
# Just run - gavel will find and load .env automatically
gavel oneshot run --eval test_os
```

**Alternative: Export manually (if not using `.env`)**

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
export OPENAI_API_KEY=sk-your-openai-key-here
gavel oneshot run --eval test_os
```

**Alternative: Inline for one-off runs**

```bash
ANTHROPIC_API_KEY=sk-... gavel oneshot run --eval test_os
```

---

## Security Best Practices

✅ **DO:**
- Store API keys in `.env` file (local development)
- Use environment variables in CI/CD pipelines
- Use `{{VAR_NAME}}` syntax in config files
- Keep `.env` in `.gitignore` (already configured)

❌ **DON'T:**
- Hardcode API keys in `agents.json` files
- Commit `.env` to git
- Store keys in public repositories

---

## Environment Variable Reference

| Variable | Provider | Required? | Example |
|----------|----------|-----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic (Claude) | Yes (if using Claude) | `sk-ant-api03-...` |
| `OPENAI_API_KEY` | OpenAI (GPT) | Yes (if using GPT) | `sk-...` |
| `GOOGLE_API_KEY` | Google (Gemini) | Optional | `AIza...` |
| `OLLAMA_BASE_URL` | Ollama (local) | Optional | `http://localhost:11434` |

---

## Troubleshooting

### Error: "Environment variable 'ANTHROPIC_API_KEY' not set"

**Cause:** Gavel can't find your API key.

**Fix:**
1. Verify `.env` file exists in project root
2. Verify `.env` contains: `ANTHROPIC_API_KEY=sk-...`
3. Run `gavel` from the project root (where `.env` is located)
4. If still failing, export manually: `export ANTHROPIC_API_KEY=sk-...`

### Error: "API key validation failed"

**Cause:** API key is invalid or expired.

**Fix:**
1. Check your API key at https://console.anthropic.com
2. Regenerate key if needed
3. Update `.env` with new key

---

## Next Steps

Once API keys are configured:

```bash
# Run your first evaluation
gavel oneshot run --eval test_os

# View run history
gavel oneshot list

# Check system health
gavel health
```

For more details, see the [CLI Reference](docs/cli-reference/) and [Examples](docs/examples/).
