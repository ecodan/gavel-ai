---
summary: "Three parallel partitions implement the remaining gavel-uplevel scope. feat/judge-types adds 4 DeepEval types to JUDGE_TYPE_MAP. feat/judge-config adds markdown_path judge loading and {{key}} criteria templating in judge_runner.py. feat/schema-docs authors the two schema reference docs and updates CLAUDE.md. All partitions merge to initiative/gavel-uplevel; the initiative merges to master via a single PR."
phase: "tasks"
when_to_load:
  - "When selecting the next implementation task or reviewing completion state."
  - "When checking partition progress, PR boundaries, or execution sequencing."
depends_on:
  - "prd.md"
  - "tech-design.md"
  - "approach.md"
modules:
  - "src/gavel_ai/judges/deepeval_judge.py"
  - "src/gavel_ai/core/steps/judge_runner.py"
  - "src/gavel_ai/models/config.py"
  - "docs/specs/"
  - "CLAUDE.md"
index:
  partition_judge_types: "## Partition: feat/judge-types"
  partition_judge_config: "## Partition: feat/judge-config"
  partition_schema_docs: "## Partition: feat/schema-docs"
  initiative_boundary: "## Initiative Boundary"
next_section: "## Partition: feat/judge-types"
---

# Tasks: gavel-uplevel

## Partition: feat/judge-types

- [x] Verify that `ToxicityMetric`, `ConversationCompletenessMetric`, `ConversationalGEval`, and `TurnRelevancyMetric` are importable from the version of `deepeval` pinned in `pyproject.toml`; note any that are unavailable and plan a conditional guard <!-- id: 1 -->
- [x] Add the 4 new types to the `try: from deepeval... except ImportError: pass` import block in `judges/deepeval_judge.py` (or add conditional guards for any unavailable types) <!-- id: 2 -->
- [x] Add all 4 entries to `DeepEvalJudge.JUDGE_TYPE_MAP`: `"deepeval.toxicity"` → `ToxicityMetric`, `"deepeval.conversation_completeness"` → `ConversationCompletenessMetric`, `"deepeval.conversational_geval"` → `ConversationalGEval`, `"deepeval.turn_relevancy"` → `TurnRelevancyMetric` <!-- id: 3 -->
- [x] Add unit tests for all 4 new types in `tests/unit/` (mock deepeval metric classes; follow the existing `test_deepeval_judge.py` pattern); all 4 types must construct without error and appear in `JudgeRegistry.list_available()` <!-- id: 4 -->
- [x] Update CLI help text in `cli/commands/oneshot.py` to include recommended thresholds: Toxicity/Hallucination: 0.85–0.95; AnswerRelevancy/Faithfulness: 0.65–0.80; ConversationCompleteness: 0.70–0.85 <!-- id: 5 -->
- [x] Update the conversational eval scaffold in `cli/scaffolding.py` to include `conversation_completeness` and `conversational_geval` judges in the default conversational `eval_config.json` template (FR-2.2) <!-- id: 6 -->
- [x] Run `uv run pytest -m unit` and confirm no regressions <!-- id: 7 -->

## Partition: feat/judge-config

- [x] Read `src/gavel_ai/models/config.py` and verify whether `JudgeConfig` has a `markdown_path: Optional[str]` field; add `markdown_path: Optional[str] = None` if absent <!-- id: 10 -->
- [x] Add `_render_judge_template(template: str, context: dict) -> str` helper in `judge_runner.py`: iterate over context keys and call `template.replace(f"{{{{{key}}}}}", str(value))`; missing keys leave placeholder unchanged <!-- id: 11 -->
- [x] Add `_build_render_context(scenario: Scenario) -> dict` helper in `judge_runner.py`: if `scenario.input` is a dict unpack its keys; if it is a string add it as `{"input": value}`; then merge in `scenario.metadata` keys <!-- id: 12 -->
- [x] Add `_load_markdown_judge_config(markdown_path_str: str, eval_dir: Path) -> dict` helper in `judge_runner.py`: validate the resolved path is within `eval_dir` (raise `ConfigError` if not), read the file, and parse `## Criteria`, `## Evaluation Steps`, `## Threshold`, `## Guidelines` sections (missing sections silently absent) <!-- id: 13 -->
- [x] Wire `_load_markdown_judge_config` into the judge config resolution stage of `judge_runner.py`: when `judge_config.markdown_path` is set, call the helper and merge parsed fields into the judge config dict (after `config_ref` resolution) <!-- id: 14 -->
- [x] Wire `_render_judge_template` in `judge_runner.py`: after all config resolution, apply to `criteria` (str) and to each item in `evaluation_steps` (list[str]) using the scenario context built by `_build_render_context` <!-- id: 15 -->
- [x] Add unit tests covering: criteria substitution with known key, unknown key passthrough, `evaluation_steps` list rendering, markdown section parsing (all 4 sections present, missing sections, threshold as float), path traversal rejection <!-- id: 16 -->
- [x] Run `uv run pytest -m unit` and `uv run pytest -m integration` and confirm no regressions <!-- id: 17 -->

## Partition: feat/schema-docs

- [x] Read `src/gavel_ai/models/config.py`, `src/gavel_ai/models/runtime.py`, `src/gavel_ai/models/scenarios.py`, and `src/gavel_ai/models/agents.py` to enumerate all field names, types, and defaults for config and output schemas <!-- id: 20 -->
- [x] Read `src/gavel_ai/core/contexts.py` (`snapshot_run_config`, `.workflow_status`, `.config/` structure) and `src/gavel_ai/telemetry/` to enumerate output artifact fields <!-- id: 21 -->
- [x] Author `docs/specs/schema-configs.md` documenting: all `eval_config.json` fields, all `agents.json` fields (`_models` entries and agent entries), `scenarios.json` scenario field schema, and judge config fields (`type`, `threshold`, `config`, `config_ref`, `markdown_path`, `criteria`, `evaluation_steps`) with types and defaults <!-- id: 22 -->
- [x] Author `docs/specs/schema-outputs.md` documenting: `results_raw.jsonl` record fields, `results_judged.jsonl` record fields, `run_metadata.json` fields, `telemetry.jsonl` span fields, and `.config/` snapshot directory structure including `snapshot_metadata.json` <!-- id: 23 -->
- [x] Add reference links to both schema docs in `CLAUDE.md` under a `## Schema Reference` section (or append to existing References section if present) <!-- id: 24 -->
- [x] Verify both files exist and are non-empty: `ls docs/specs/schema-configs.md docs/specs/schema-outputs.md` <!-- id: 25 -->

## Initiative Boundary

- [x] Open PR: initiative/gavel-uplevel → master and await merge approval before continuing <!-- id: 100 -->
