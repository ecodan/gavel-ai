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

Read `references/cli-reference.md` (in this skill's directory) to confirm the
current set of available commands before advising the user. If the reference
seems stale (user reports a command that is missing), suggest running
`python scripts/update_cli_reference.py` from the skill directory.

### 1. Identify the task

Ask one clarifying question if needed, or infer from context:

| User intent | Action |
|---|---|
| Start a new eval | `gavel oneshot create`, `gavel conv create`, or `gavel autotune create` |
| Configure an eval | Read & edit `eval_config.yaml`, judge config, model config |
| Add / format scenario data | Create or edit scenario JSONL/TOML files |
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
   directory structure.
3. Walk through each generated config file and explain what to fill in.

**Scenario data**
1. Read existing scenario files if present.
2. Help the user create, select, or reformat scenario records into the
   expected format (JSONL rows with `input`, `expected_output`, and any
   custom fields).
3. Validate that scenario IDs are unique if the eval enforces that.

**Running & debugging**
1. Run the eval with `gavel oneshot run --eval <name>` (add `--scenarios`
   to filter if needed).
2. If the run fails, read the full error output and trace it to:
   - Config file issues (missing keys, wrong types)
   - Scenario data format errors
   - API / model authentication problems
   - Dependency or environment issues
3. Propose and apply targeted fixes, then re-run.

**Judging**
1. After a successful run, retrieve the run ID from the output.
2. Run `gavel oneshot judge --run <run-id>` to apply judge pipeline steps.
3. Explain what each judge step evaluated.

**Reporting & results**
1. Run `gavel oneshot report --run <run-id>`.
2. Read the report output and explain in plain language:
   - Overall pass/fail rate and key metrics
   - Which scenarios failed and why
   - Comparison to any milestone runs
   - Actionable next steps (prompt tuning, data improvements, etc.)

### 3. Listing & milestones

- `gavel oneshot list` — show past runs (optionally filter by eval name)
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
