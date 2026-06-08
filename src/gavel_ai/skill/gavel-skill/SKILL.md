---
name: gavel-skill
description: >
  Use when the user mentions "gavel", "gavel-ai", or asks for help running,
  configuring, or interpreting AI evaluations with the gavel-ai framework.
  Covers eval setup, golden dataset preparation, scenario formatting, CLI
  execution, judge selection, debugging, and results interpretation.
  Does NOT trigger on general requests to "evaluate" code, bugs, or written
  documents that are unrelated to the gavel-ai eval system.
license: Apache-2.0
argument-hint: "[eval-name or question about gavel]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

## Instructions

When this skill fires, you are the **Gavel Eval Assistant** — a hands-on
helper for every stage of working with the gavel-ai evaluation framework.

### 0. Orient

Before advising the user, read the relevant reference files:

| Topic | File |
|---|---|
| CLI commands & options | `references/cli-reference.md` |
| Config file schemas | `references/config-schema.md` |
| Scenario format & dataset tips | `references/scenario-format.md` |
| Judge types & metrics | `references/judges-reference.md` |

Read only the references relevant to the user's current step. You do not
need to read all four on every invocation.

If a reference seems stale (e.g., a user reports a missing command), suggest
running `python scripts/update_cli_reference.py` from the skill directory.

---

### 1. Identify the task

Ask one clarifying question if needed, or infer from context:

| User intent | Action |
|---|---|
| Start a new eval | Walk the full setup flow (§2) |
| Format existing data for gavel | Help with scenario JSON structure (§3) |
| Configure models / agents | Help with `agents.json` (§4) |
| Choose and configure judges | Help with judge selection (§5) |
| Run an eval | `gavel oneshot run --eval <name>` (§6) |
| Debug a run | Read stderr, inspect output files (§6) |
| Judge results | `gavel oneshot judge --run <run-id>` (§7) |
| Generate a report | `gavel oneshot report --run <run-id>` (§7) |
| Interpret results | Explain scores, regressions, milestones (§8) |
| Generate scenarios (conv) | `gavel conv generate --eval <name>` |
| Automatically optimize a prompt | Walk the autotune setup flow (§13) |

---

### 2. Full eval setup flow

Walk the user through these stages in order. Each has its own section below.

```
Stage 1 — Initialize project (gavel init)
Stage 2 — Choose your golden dataset
Stage 3 — Format data into scenarios.json
Stage 4 — Create eval scaffold (gavel oneshot create)
Stage 5 — Configure agents.json (models to test)
Stage 6 — Choose and configure judges
Stage 7 — Run end-to-end (run → judge → report)
```

---

### 3. Stage 1 — Initialize the project

If the user has not yet run `gavel init`, do it first:

```bash
gavel init                          # writes .gavel/config.json, uses ./evals as root
gavel init --eval-root ./evals      # or specify explicitly
```

All subsequent commands resolve the eval root via: `--eval-root` flag →
`GAVEL_EVAL_ROOT` env var → `.gavel/config.json` → `.gavel/evaluations`.
Running `gavel init` once means users never need to pass `--eval-root` again.

---

### 4. Stage 2 — Choose your golden dataset

A "golden dataset" is a set of inputs with known-good expected outputs used
to measure model quality. Help the user think through:

**Where does ground truth come from?**
- **Human-labeled data**: Most reliable. Have subject matter experts write
  `expected_behavior` strings for each scenario.
- **Production logs**: Export real user inputs. Sample representatively, not
  just the most frequent queries. Anonymize PII.
- **Existing test cases**: If the team has a test suite, the inputs and
  assertions may translate directly.
- **Known failure cases**: Seed with past incidents, bug reports, and edge
  cases — these are the most valuable scenarios.

**Dataset sizing guidelines** (see `references/scenario-format.md`):
- 5–20 scenarios: smoke test during development
- 50–200: representative coverage for iteration
- 200–1000+: statistically reliable production eval

**Golden data quality rules**:
1. Expected outputs must be written by humans, not by the model being evaluated.
2. `expected_behavior` should describe what the model **should do**, not a
   verbatim transcript. Be specific enough to be measurable.
3. Cover happy path, edge cases, adversarial inputs, and domain breadth.
4. Scenarios should be diverse — 100 high-quality diverse scenarios beat
   1000 near-duplicates.

---

### 5. Stage 3 — Format data into scenarios.json

Read `references/scenario-format.md` for the full field reference. Key points:

**Minimum required fields:**
```json
[
  {
    "id": "unique-stable-id",
    "input": "the question or prompt",
    "expected_behavior": "what a correct response looks like"
  }
]
```

**ID conventions**: Use readable, stable IDs like `"refund-policy-001"` or
`"edge-empty-input"`. IDs appear in all output files — good names make
debugging much faster.

**When the model produces structured output** (classification, extraction):
```json
{
  "id": "classify-001",
  "input": "I want to cancel my subscription",
  "expected": "cancellation",
  "metadata": { "category": "account", "source": "prod-logs" }
}
```

**When your eval uses RAG / context**:
```json
{
  "id": "rag-001",
  "input": {
    "query": "What is the refund window?",
    "retrieval_context": ["Returns accepted within 30 days of purchase."]
  },
  "expected_behavior": "The refund window is 30 days."
}
```

Help the user convert their existing data format. Common transformations:
- CSV → JSON: read rows, write one scenario object per row
- DB export → JSON: map columns to `id`, `input`, `expected_behavior`, `metadata`
- Log entries → JSON: extract query field as `input`, use log label as `expected`

Validate before running:
- All `id` values are unique
- No empty `input` values
- Judge-required fields are present (see `references/scenario-format.md`)
- Valid JSON (no trailing commas, no comments)

---

### 6. Stage 4 — Create the eval scaffold

```bash
gavel oneshot create --eval <name>
# or for deterministic classification/regression evals:
gavel oneshot create --eval <name> --template classification
gavel oneshot create --eval <name> --template regression
```

Show the user the generated directory structure and explain what each file does:
```
{eval_root}/{eval_name}/
├── config/
│   ├── eval_config.json    ← workflow, test subjects, judges, scenarios config
│   ├── agents.json         ← models to test
│   └── prompts/
│       └── *.toml          ← prompt templates (local evals)
└── data/
    └── scenarios.json      ← paste your formatted scenarios here
```

Copy the user's formatted scenarios into `data/scenarios.json`.

---

### 7. Stage 5 — Configure agents.json (models to test)

Read `references/config-schema.md` for the full schema. Walk the user through:

1. **Define models in `_models`**: One entry per model variant to test.
   ```json
   {
     "_models": {
       "claude-haiku": {
         "model_provider": "anthropic",
         "model_family": "claude",
         "model_version": "claude-haiku-4-5-20251001",
         "model_parameters": { "temperature": 0.3, "max_tokens": 1024 },
         "provider_auth": { "api_key": "{{ANTHROPIC_API_KEY}}" }
       }
     }
   }
   ```

2. **Wire variants in eval_config.json**: Set `variants` to the model keys you
   want to test side-by-side:
   ```json
   { "variants": ["claude-haiku"] }
   ```

3. **Set the prompt** (`test_subjects[].prompt_name`): Must match a `.toml`
   file in `config/prompts/`. Prompt files use `{{var}}` syntax for scenario
   field substitution. Literal `{` and `}` in prompt text (JSON examples,
   code snippets) are passed through unchanged.

4. **Set API keys**: Use environment variables — `{{ANTHROPIC_API_KEY}}` is
   resolved from the process environment in DeepEval judge model creation.
   For the main LLM call path, export the key directly:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

---

### 8. Stage 6 — Choose and configure judges

Read `references/judges-reference.md` for the full decision guide. Key questions:

**What are you measuring?**
- Response quality / correctness → `deepeval.geval` (most flexible)
- Staying on topic → `deepeval.answer_relevancy`
- RAG grounding → `deepeval.faithfulness` + `deepeval.hallucination`
- Retrieval quality → `deepeval.contextual_precision` + `deepeval.contextual_recall`
- Safety / toxicity → `deepeval.toxicity`
- Multi-turn conversation → `deepeval.conversation_completeness` + `deepeval.turn_relevancy`
- Classification labels (no LLM) → `classifier`
- Numeric predictions (no LLM) → `regression`

**For `deepeval.geval`, write good criteria**:
- `criteria`: one sentence — "Does the response correctly answer the user's question
  with accurate, complete information?"
- `evaluation_steps`: 3–6 concrete testable checks, most important first.
  Vague steps produce inconsistent scores.

**Threshold guidance**:
- Start with `0.7` for most judges (→ score ≥ 7)
- Safety judges: `0.85–0.95`
- Faithfulness/hallucination: `0.8+`
- Style/open-ended: `0.6`

Add judges to `test_subjects[].judges[]` in `eval_config.json`. Confirm that
each judge's required scenario fields are present in `data/scenarios.json`.

---

### 9. Stage 7 — Run end-to-end

**Full pipeline:**
```bash
# Step 1: Run scenarios through the model(s)
gavel oneshot run --eval <name>

# Step 2: Apply judges to the run output
gavel oneshot judge --run <run-id>

# Step 3: Generate HTML/Markdown report
gavel oneshot report --run <run-id>
```

Run ID is printed by `gavel oneshot run` and also visible via:
```bash
gavel oneshot list --eval <name>
```

**Smoke-test with a subset first:**
```bash
gavel oneshot run --eval <name> --scenarios 1-5
```

If the run fails, go to §10.

---

### 10. Debugging a failed run

Gavel prints a Rich panel to stderr with the human-readable cause and the path
to `run.log`. Always read the panel message first, then `run.log` for full detail.

Trace failures to:

| Symptom | Likely cause | Fix |
|---|---|---|
| `ConfigError: variant not found` | `variants` key in `eval_config.json` doesn't match `_models` key in `agents.json` | Align the names exactly |
| `ConfigError: prompt file not found` | `prompt_name` points to a `.toml` that doesn't exist | Check `config/prompts/` |
| `ConfigError: placeholder not found` | `{{var}}` in prompt has no matching scenario field | Add the field to scenarios or fix the prompt |
| `ConfigError: expected_output not resolvable` | GEval judge has no `expected_behavior` and no `field_mapping.expected_output` | Add `expected_behavior` to scenarios or configure `field_mapping` |
| Auth error | API key not set or invalid | Export the env var |
| `MissingTestCaseParamsError` | Judge needs a field (`context`, `retrieval_context`) not in the scenario | Add the required field |
| All scores are 0 or 1 | `strict_mode: true` on geval judge | Remove `strict_mode` or confirm it's intentional |
| Deterministic results missing | `classifier`/`regression` judge result isn't in `results_judged.jsonl` | Expected — these appear only in the HTML report, not JSONL |

---

### 11. Interpreting results

After `gavel oneshot report`:
- Open `runs/{run_id}/report.html` for the full visual report
- Read `runs/{run_id}/results_judged.jsonl` for raw per-scenario scores

**Reading judge results**: Look at `judges[].reasoning` for failed scenarios.
This explains *what* the judge found wrong.

**Common score patterns**:
| Pattern | Diagnosis |
|---|---|
| Consistently low across all scenarios | Prompt too vague or wrong model for the task |
| Low on specific scenario categories | Dataset coverage gap or prompt blind spot |
| Low faithfulness but high geval | Model generates plausible but ungrounded content |
| Low answer_relevancy | Model hedging, refusing, or going off-topic |
| Inconsistent scores for similar scenarios | Judge criteria / evaluation_steps are ambiguous |

**Milestone workflow**:
```bash
# After a good baseline run:
gavel oneshot milestone --run <run-id> --comment "baseline after prompt v2"
# After a change, compare new scores against milestone
```

A regression is a judge score that drops more than 1 point on average, or an
increase in scenarios scoring below the threshold.

---

### 12. Listing & milestone management

```bash
gavel oneshot list                              # all runs
gavel oneshot list --eval <name>               # filter by eval
gavel oneshot milestone --run <id> --comment "..." # mark baseline
gavel oneshot milestone --run <id> --remove    # remove milestone
```

---

### 13. Autotune — automated prompt optimization

Autotune runs an iterative `execute → judge → improve` loop: an LLM
meta-optimizer (`TuningAgent`) rewrites the prompt based on judge feedback each
round, until the score converges, plateaus, degrades, or `max_rounds` is
reached. Walk the user through these seven stages in order.

#### Stage 1 — Prerequisite check

Before starting, confirm:
- A working `oneshot` eval already exists for this prompt (it has run at least once successfully)
- `workflow_type` in `eval_config.json` is **not** already `"autotune"` (if it is, skip to Stage 5 — setup is done)
- At least one **LLM judge** (e.g. `deepeval.geval`) is configured — autotune needs a numeric score signal; deterministic judges (`classifier`/`regression`) alone are not enough
- `gavel autotune create` is available (`gavel autotune --help`)

If any prerequisite is missing, explain what's missing and how to fix it before continuing — don't proceed with a half-configured setup.

#### Stage 2 — Config setup

Either scaffold a new eval with `gavel autotune create --eval <name>` (writes a
ready-to-edit `eval_config.json` with `workflow_type: "autotune"` and a
`tuning` block already in place), or add a `tuning` block to an existing
`eval_config.json`:

```json
"tuning": {
  "max_rounds": 5,
  "convergence_threshold": 0.02,
  "target_score": 0.8,
  "degradation_tolerance": 0.05,
  "tuning_agent_model": "<model-id-from-agents-json>",
  "tuning_agent_temperature": 0.7
}
```

| Field | Meaning |
|---|---|
| `max_rounds` | Hard upper bound on iterations (recommend 3–5 for first runs) |
| `convergence_threshold` | Stop when `\|current_score - previous_score\| < threshold` (0.0–1.0 scale) |
| `target_score` | Optional early stop once `avg_score` reaches this value (0.0–1.0 scale, e.g. `0.8` = 80%) |
| `degradation_tolerance` | Stop if `avg_score` drops by more than this amount round-over-round |
| `tuning_agent_model` | Must match a key under `_models` in `agents.json` — this is the meta-optimizer LLM |
| `tuning_agent_temperature` | Temperature for the meta-optimizer's rewrite calls |

#### Stage 3 — Meta-prompt setup

Autotune ships with a bundled meta-prompt that instructs the optimizer LLM how
to rewrite the prompt from judge feedback. Most users don't need to touch it.

- Default (bundled): `processors/autotune_template/autotune.toml`
- Override: create `config/prompts/autotune.toml` in the eval directory — autotune prefers this if present
- Available `{{var}}` template variables: `{{current_prompt}}`, `{{judge_feedback}}`, `{{avg_score}}`, `{{iteration}}`, `{{max_rounds}}`, `{{target_score}}`, `{{placeholder_vars}}`
- Only override if the bundled guidance is producing poor rewrites for this domain

#### Stage 4 — Run autotune

```bash
gavel autotune run --eval <name>
gavel autotune run --eval <name> --run <run-id>   # resume an interrupted run
```

Expected output: a per-iteration progress table (prompt version, score,
improvement, convergence reason), a convergence summary, and the path to
`runs/<run_id>/report.html`. On failure, gavel prints a Rich error panel to
stderr — read it the same way as described in §10.

#### Stage 5 — Interpret the report

Open `runs/<run_id>/report.html`:
- **Score Progression Table** — look for steady improvement; a plateau signals convergence, a drop signals a degradation stop
- **Per-Judge Detail** — if one judge's trend diverges sharply from the others, check that judge's `criteria`/`evaluation_steps` for misconfiguration before trusting the overall trend
- **Best Prompt Version** — the highlighted row is the iteration to promote
- Treat a single run as a starting point, not a final answer — re-run on fresh scenarios to validate that the improvement generalizes

#### Stage 6 — Promote the best prompt

1. Open `runs/<run_id>/prompts.toml` and find the highlighted `[v{N}]` (the best version from the report)
2. Copy its `prompt = "..."` value
3. Open the eval's permanent `config/prompts/<eval-name>.toml`
4. Append it as a new versioned entry, e.g. `v2 = '''...'''`
5. Update `eval_config.json` → `test_subjects[0].prompt_name` to `"<eval-name>:v2"` to pin it, or leave it as `"<eval-name>:latest"` to always use the newest version
6. Validate on the full scenario set: `gavel oneshot run --eval <name>`

#### Stage 7 — Next iteration

Ask: "Do you want to keep tuning from the promoted prompt?" If yes, start a
**fresh** autotune run — don't resume the previous run's `prompts.toml`. The
newly promoted prompt becomes the new `v1` baseline for the next round of
tuning.

---

### 14. Keeping references current

When CLI or config schemas change:
```bash
python scripts/update_cli_reference.py
```

Then check `references/config-schema.md` and `references/judges-reference.md`
for any fields that need updating.

## Scripts

- `scripts/update_cli_reference.py` — regenerates `references/cli-reference.md`
  from live `gavel --help` output. Run after any CLI change.

## References

- `references/cli-reference.md` — gavel CLI command reference (all options, envvars)
- `references/config-schema.md` — full schema for `eval_config.json`, `agents.json`, prompt TOML; project init
- `references/scenario-format.md` — scenario JSON format, judge-required fields, dataset best practices
- `references/judges-reference.md` — all judge types (LLM + deterministic), config, score interpretation, selection guide
