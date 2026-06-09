---
boundary: "partition-complete"
initiative: "external-runner"
---

# Handoff: external-runner — P3 + P5 merged, P4 + P6 + P7 remain

## Just completed

Two partitions merged into `initiative/external-runner` (now at `e3b093d`):

- **P3 feat/external-script-processor** — `ScriptInputProcessor` (3-seam ADR-10), tmp-dir lifecycle, asyncio subprocess, path-confinement fix (`+ os.sep`), `classify_external_outcome` wired, `scenario_processor.py` extended for `external/script` routing, fixture scripts under `tests/fixtures/scripts/`, 13 unit tests + 6 integration tests, all green.
- **P5 feat/external-runner-schemas** — `ExternalTaskRequest` + `ExternalJudgeRequest` Pydantic models in `models/runtime.py`, `scripts/generate_external_schemas.py`, `docs/specs/schemas/` JSON files (3 schemas), `docs/specs/schema-external-runner.md`, cross-links in `schema-configs.md`/`schema-outputs.md`, 15 unit tests, all green.

## Approved/authoritative state

- `.cicadas/active/external-runner/tasks.md` — P3 tasks 28–40 `[x]`, P5 tasks 48–54 `[x]`; next: P4 `feat/external-judge-delegation` (tasks 41–47) and P6 `feat/external-runner-scaffolds` (tasks 55–63)
- `.cicadas/active/external-runner/approach.md` — `## Partition 4` (judge delegation) and `## Partition 6` (scaffolds) for next scope
- `initiative/external-runner` at `e3b093d` — authoritative, pushed

## DAG state after P3 + P5

```
Foundation ✓ → HTTP ✓ → ScriptProcessor ✓ → JudgeDelegation (P4) — UNBLOCKED
Foundation ✓ → Schemas ✓ → Scaffolds (P6) — UNBLOCKED (wait for P4 first for round-trip fixtures)
HTTP ✓ + ScriptProcessor ✓ → SkillFlows (P7) — UNBLOCKED
```

P4 unblocks P6's round-trip fixture tests (approach.md notes P6 should use "real Gavel-generated request fixtures from Partitions 2-4"). P7 can run in parallel with P4/P6.

## Next action

Three partitions are next. Recommended execution order:
1. **P4 `feat/external-judge-delegation`** (tasks 41–47) — extends `judge_runner.py`/`JudgeExecutor` to route external-judge configs through `ExternalHttpProcessor`/`ScriptInputProcessor`. Depends on P3 + P2, both merged. Can start now.
2. **P7 `feat/external-runner-skill-flows`** (tasks 64–70) — extends `SKILL.md` §2/§6 for `external` setup/debug flows. Can run in parallel with P4.
3. **P6 `feat/external-runner-scaffolds`** (tasks 55–63) — scaffold base classes and `_materialize.py`. Depends on P5 (merged). Can start after P4 for better fixture coverage, but P5 schemas are sufficient to start.

## Register next branches

```bash
# P4
python .claude/skills/cicadas/scripts/cicadas.py branch feat/external-judge-delegation \
  --intent "Extend JudgeRunnerStep/JudgeExecutor to delegate external judge execution via ExternalHttpProcessor/ScriptInputProcessor" \
  --modules "core/steps/judge_runner.py,models/config.py" \
  --initiative external-runner

# P6
python .claude/skills/cicadas/scripts/cicadas.py branch feat/external-runner-scaffolds \
  --intent "Scaffold base classes RemoteSystemUnderTest/ScriptSystemUnderTest, _materialize.py, eval-creation hook" \
  --modules "src/gavel_ai/scaffolds/" \
  --initiative external-runner

# P7
python .claude/skills/cicadas/scripts/cicadas.py branch feat/external-runner-skill-flows \
  --intent "Extend SKILL.md setup/debug flows for external/http+script configuration and two-tier-failure guidance" \
  --modules "src/gavel_ai/skill/gavel-skill/SKILL.md,src/gavel_ai/skill/gavel-skill/references/cli-reference.md" \
  --initiative external-runner
```

## Reload list

- `.cicadas/active/external-runner/tasks.md` front matter + `## Partition: feat/external-judge-delegation` (tasks 41–47)
- `.cicadas/active/external-runner/approach.md` front matter + `### Partition 4` section
- `src/gavel_ai/core/steps/judge_runner.py` — existing JudgeRunnerStep for extension scope
- `src/gavel_ai/processors/external_http_processor.py` — reference for routing to reuse
- `src/gavel_ai/processors/script_processor.py` — reference for routing to reuse

## Carry forward

- **P5 Code Review advisories (non-blocking)**:
  - `generate_external_schemas.py:65` — shorter transport note overwrites model docstring in schema; acceptable for now
  - Test suite: no negative validation tests (schema permissiveness not checked); `test_generation_script_exits_zero` could race under xdist (mark serial if needed)
  - `SCHEMA_TARGETS` type annotation: use `Type[BaseModel]` instead of bare `type`
- **Version bump**: `pyproject.toml` is now `0.2.0` (bumped by P5 agent when adding jsonschema dep); test_cli.py updated accordingly
- **No PRs until initiative done** — all partitions merge directly to `initiative/external-runner`
