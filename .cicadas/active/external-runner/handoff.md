---
boundary: "partition-complete"
initiative: "external-runner"
---

# Handoff: external-runner — HTTP path complete, PR open

## Just completed

`feat/external-http-rename` is **committed** at `755d6a2` and **PR #6 is open** (`feat/external-http-rename` → `initiative/external-runner`). All 12 partition tasks [x]. Code Review done (no blocking findings). Branch has **not yet been merged** — awaiting Builder merge approval.

## Approved/authoritative state

- `.cicadas/active/external-runner/tasks.md` → `## Partition: feat/external-http-rename` (all [x]); `next_section: feat/external-script-processor`
- `.cicadas/active/external-runner/approach.md` → `## Partitions DAG` for sequencing; `### Partition 3: Script Processor` for next scope
- `.cicadas/registry.json` → `external-runner` initiative + `feat/external-http-rename` branch registered
- PR: https://github.com/ecodan/gavel-ai/pull/6

## Next action

**Wait for Builder to confirm PR #6 is merged.** Once merged:

1. Merge `feat/external-http-rename` into `initiative/external-runner` (happens via PR merge).
2. Register the next feature branch(es) — both are now DAG-unblocked and can run in parallel:
   - `feat/external-runner-schemas` (tasks 48–54)
   - `feat/external-script-processor` (tasks 28–40)
3. Start with whichever the Builder prefers (or both in parallel worktrees).

```bash
# After PR merge, register script processor branch:
python .claude/skills/cicadas/scripts/cicadas.py branch feat/external-script-processor \
  --intent "Implement ScriptInputProcessor: tmp-dir lifecycle, asyncio subprocess, path-confinement, classify_external_outcome wiring" \
  --modules "processors/script_processor.py,core/steps/scenario_processor.py" \
  --initiative external-runner

# Or schemas branch:
python .claude/skills/cicadas/scripts/cicadas.py branch feat/external-runner-schemas \
  --intent "Finalize ExternalTaskRequest/ExternalJudgeRequest models, schema-generation script, schema-external-runner.md doc" \
  --modules "docs/specs/schema-external-runner.md,models/runtime.py" \
  --initiative external-runner
```

## Reload list

On resume:
- `.cicadas/active/external-runner/tasks.md` — front matter + `## Partition: feat/external-script-processor` (tasks 28–40) or `## Partition: feat/external-runner-schemas` (tasks 48–54)
- `.cicadas/active/external-runner/approach.md` — front matter + `### Partition 3` and `### Partition 5` sections
- `.cicadas/registry.json` — verify branch registration before starting work
- `src/gavel_ai/processors/external_http_processor.py` — the reference implementation; script processor mirrors this structure

Do **not** reload Foundation or HTTP-rename implementation details unless Partition 3 needs cross-reference.

## Carry forward

- **Advisory from Code Review (non-blocking)**:
  - `_parse_response`: broad `except` for `ExternalResponseEnvelope` parse fallback — DEBUG log in a future pass
  - `subject_cfg` declared in two scopes in `scenario_processor.py` — no bug
- **PR #6 still open**: Builder must confirm merge before registering next feature branches
- **Foundation worktree** at `/Users/dan/dev/code/projects/python/gavel-ai-feat-external-runner-foundation` still exists — safe to delete after PR #6 merges (Foundation is already in initiative branch)
- **Partition sequencing reminder**: both transports (HTTP + script) must merge before judge delegation (Partition 4) and skill-flows (Partition 7); schemas (Partition 5) must merge before scaffolds (Partition 6)
