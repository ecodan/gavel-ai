
# Tweaklet: unify-template-syntax

## Intent

Standardize all gavel-ai user-facing template variable syntax to `{{var}}` everywhere —
prompt `.toml` files, judge criteria, and the autotune meta-prompt template.

Currently gavel uses two syntaxes: `$var` (Python `string.Template`) in prompt files and
`{{key}}` (regex substitution) in judge criteria. This is confusing UX. `{{var}}` is the
dominant convention in the LLM tooling ecosystem (LangChain, LlamaIndex, Jinja2, Handlebars,
Mustache) and should be the single model users learn.

The original switch to `$var` was made to avoid Jinja2's full template parser choking on
literal `{` and `}` in prompt text (JSON examples, code snippets). The fix is not to abandon
the `{{var}}` syntax — it's to replace full Jinja2 rendering with a lightweight regex
substitution that only matches `{{identifier}}` and ignores all other braces.

## Proposed Change

### 1. `src/gavel_ai/core/steps/scenario_processor.py`

Replace `string.Template` with a regex renderer in `_render_prompt()`:

```python
import re

def _render_prompt(self, template_text: str, variables: dict) -> str:
    def replace(m: re.Match) -> str:
        key = m.group(1)
        if key not in variables:
            raise ConfigError(
                f"Prompt placeholder '{{{{{key}}}}}' has no matching scenario field. "
                f"Available fields: {sorted(variables.keys())}"
            )
        return str(variables[key])
    return re.sub(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', replace, template_text)
```

Update the placeholder extraction used by `ValidatorStep` to match `{{var}}` patterns:

```python
# was: re.findall(r'\$\{?([a-zA-Z_][a-zA-Z0-9_]*)\}?', prompt_text)
re.findall(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', prompt_text)
```

### 2. Live prompt `.toml` files

Update all active `config/prompts/` files from `$var` to `{{var}}`:

| File | Change |
|---|---|
| `.gavel/evaluations/test_os/config/prompts/assistant.toml` | `$input` → `{{input}}` |
| `.gavel/evaluations/media-lens-headline-extraction/config/prompts/default.toml` | `$input` → `{{input}}` |
| `.gavel/evaluations/media-lens-interpretation/config/prompts/default.toml` | `$input` → `{{input}}` |
| `.gavel/evaluations/media-lens-daily-summary/config/prompts/assistant.toml` | `$input` → `{{input}}` |

Run snapshot copies in `.gavel/evaluations/*/runs/*/` are **not** updated — they are
historical records of what was actually executed.

### 3. Documentation

- `CLAUDE.md` runtime conventions: update `$var` → `{{var}}` in prompt template note
- `src/gavel_ai/skill/gavel-skill/references/config-schema.md`: update prompt template syntax example
- Canon `tech-overview.md` and `summary.md`: update conventions section

### 4. Tests

Update any test fixtures or assertions that use `$var` prompt syntax to use `{{var}}`.

## Tasks

- [x] Replace `string.Template` renderer in `scenario_processor.py` with regex `{{var}}` renderer <!-- id: 10 -->
- [x] Update placeholder extraction regex in `ValidatorStep` / `scenario_processor.py` <!-- id: 11 -->
- [x] Migrate all active `config/prompts/*.toml` files from `$var` to `{{var}}` <!-- id: 12 -->
- [x] Update test fixtures that reference `$var` prompt syntax <!-- id: 13 -->
- [x] Update CLAUDE.md, skill reference docs, and canon <!-- id: 14 -->
- [x] Run `uv run pytest -m unit && uv run pytest -m integration` — all pass <!-- id: 15 -->
- [ ] Significance Check: Does this warrant a Canon update? <!-- id: 16 -->
