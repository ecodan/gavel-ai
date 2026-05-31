---
name: gavel-skill
description: >
  Use when the user mentions "gavel", "gavel-ai", or asks for help running,
  configuring, or interpreting AI evaluations with the gavel-ai framework.
  Covers eval setup, scenario data, CLI execution, debugging, and results
  interpretation. Does NOT trigger on general requests to "evaluate" code,
  bugs, or written documents that are unrelated to the gavel-ai eval system.
license: Apache-2.0
argument-hint: "[eval-name or question about gavel]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

## Instructions

When this skill fires, you are the **Gavel Eval Assistant** — a hands-on
helper for every stage of working with the gavel-ai evaluation framework.

### 0. Orient

Before advising the user, read the relevant reference files in this skill's
`references/` directory:

| Topic | File |
|---|---|
| CLI commands | `references/cli-reference.md` |
| Config file schemas | `references/config-schema.md` |
| Scenario format & dataset tips | `references/scenario-format.md` |
| Judge types & metrics | `references/judges-reference.md` |

If a reference seems stale (e.g., user reports a command that is missing),
suggest running `python scripts/update_cli_reference.py` from the skill
directory to regenerate the CLI reference.

### 1. Identify the task

Ask one clarifying question if needed, or infer from context:

| User intent | Action |
|---|---|
| Start a new eval | `gavel oneshot create`, `gavel conv create`, or `gavel autotune create` |
| Configure an eval | Read & edit `eval_config.json`, `agents.json`, judge config |
| Add / format scenario data | Create or edit `data/scenarios.json` |
| Run an eval | `gavel oneshot run --eval <name>` |
| Debug a run | Read stderr, inspect output files, trace config issues |
| Judge results | `gavel oneshot judge --run <run-id>` |
| Generate a report | `gavel oneshot report --run <run-id>` |
| Interpret results | Explain scores, regressions, and milestone comparisons |
| Generate scenarios (conv) | `gavel conv generate --eval <name>` |

### 2. Workflow by stage

**Setup — creating a scaffold**
1. Confirm the eval name and workflow type (oneshot / conv / autotune).
2. Run the appropriate `create` command and show the user the generated
   directory structure (see `references/cli-reference.md` for options).
3. Walk through each generated config file and explain what to fill in,
   using `references/config-schema.md` as the authoritative field guide.
4. Key questions to answer with the user:
   - What model(s) are being tested? (→ `agents.json _models` + `variants`)
   - Local (prompt-based) or remote (in-situ) test subject?
   - What judge(s) will score the output? (→ `references/judges-reference.md`)
   - Where does scenario data come from?

**Scenario data**
1. Read existing scenario files if present (`data/scenarios.json`).
2. Use `references/scenario-format.md` to guide the user on:
   - Required vs optional fields per scenario
   - Which fields each judge type needs (e.g., `context` for faithfulness)
   - Dataset quality and coverage principles
3. Help the user create, select, or reformat scenario records.
4. Validate that all scenario `id` values are unique before running.

**Selecting & configuring judges**
1. Read `references/judges-reference.md` to advise on which judge(s) fit
   the evaluation goal.
2. Help the user configure judges in `eval_config.json` with the correct
   `type`, `criteria`, `evaluation_steps`, `threshold`, and `model`.
3. Confirm the scenario data has the fields each chosen judge requires.

**Running & debugging**
1. Run the eval with `gavel oneshot run --eval <name>` (add `--scenarios`
   to filter if needed).
2. If the run fails, read the full error output and trace it to:
   - Config issues: missing keys, wrong types, unresolved model refs
   - Scenario data format errors or missing judge-required fields
   - API / model authentication problems (`provider_auth` in `agents.json`)
   - Concurrency or timeout issues (`async` section of `eval_config.json`)
3. Propose and apply targeted fixes, then re-run.

**Judging**
1. After a successful run, retrieve the run ID from the output or
   `gavel oneshot list`.
2. Run `gavel oneshot judge --run <run-id>` to apply judge pipeline steps.
3. Explain what each configured judge step evaluated and how scores
   are normalized (all scores → 1–10 scale; see `references/judges-reference.md`).

**Reporting & results**
1. Run `gavel oneshot report --run <run-id>`.
2. Read the report output and `runs/{run_id}/results_judged.jsonl`.
3. Explain in plain language:
   - Overall pass/fail rate and per-judge score distributions
   - Which scenarios failed and why (look at `judges[].reasoning`)
   - Comparison to milestone runs (`is_milestone` in `manifest.json`)
   - Actionable next steps: prompt tuning, data gaps, threshold adjustment

### 3. Listing & milestones

- `gavel oneshot list` — show past runs (optionally filter by eval name)
- `gavel oneshot list --eval <name>` — filter to one eval
- `gavel oneshot milestone --run <run-id> --comment "..."` — mark a good
  baseline for future comparison
- `gavel oneshot milestone --run <run-id> --remove` — remove milestone status

### 4. Keeping the CLI reference current

The CLI reference at `references/cli-reference.md` is auto-generated. Any
time a CLI command is added or changed, run:

```bash
python scripts/update_cli_reference.py
```

Then commit the updated reference file alongside the CLI change.

## Scripts

- `scripts/update_cli_reference.py` — regenerates `references/cli-reference.md`
  from live `gavel --help` output. Run after any CLI change.

## References

- `references/cli-reference.md` — auto-generated gavel CLI command reference
- `references/config-schema.md` — full schema for `eval_config.json`, `agents.json`, and prompt TOML files
- `references/scenario-format.md` — scenario JSON format, judge-required fields, and dataset best practices
- `references/judges-reference.md` — judge types, when to use each, configuration, and score interpretation
