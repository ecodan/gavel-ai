---
summary: "Task checklist for oneshot-convergence-v1 execution. Focuses on sequential rollout starting with core logic fixes, followed by CLI refactoring and feature implementation, and concluding with robust testing."
phase: "tasks"
when_to_load:
  - "When selecting the next implementation task or reviewing completion state."
  - "When checking partition progress, PR boundaries, or execution sequencing."
depends_on:
  - "prd.md"
  - "ux.md"
  - "tech-design.md"
  - "approach.md"
modules:
  - "gavel_ai.cli.commands.oneshot"
  - "gavel_ai.processors"
  - "gavel_ai.models.runtime"
  - "tests.integration"
index:
  partition_one: "## Partition: feat/oneshot-execution-fixes"
  partition_two: "## Partition: feat/oneshot-cli-wiring"
  partition_three: "## Partition: feat/oneshot-integration"
  initiative_boundary: "## Initiative Boundary"
next_section: "## Partition: feat/oneshot-execution-fixes"
---

# Tasks: oneshot-convergence-v1

## Partition: feat/oneshot-execution-fixes

- [x] Update `RunMetadata` in `gavel_ai.models.runtime` to support `milestone` (bool) and `comment` (Optional[str]) <!-- id: 1 -->
- [x] Refactor `gavel_ai.processors.scenario_processor` to use `model_copy(deep=True)` for input scenarios <!-- id: 2 -->
- [x] Migrate `gavel_ai.processors.prompt_processor` retry loop to use `gavel_ai.core.retry.retry_with_backoff` <!-- id: 3 -->
- [x] Enhance `gavel_ai.processors.closedbox_processor` exception catching (remove bare Exception) <!-- id: 4 -->
- [x] Run unit tests to verify processor fixes `pytest tests/unit/test_scenario_processor.py tests/unit/test_prompt_processor.py tests/unit/test_closedbox_processor.py` <!-- id: 5 -->

## Partition: feat/oneshot-cli-wiring

- [x] Refactor `run` command in `gavel_ai.cli.commands.oneshot` into private helper functions to pass C901 complexity <!-- id: 10 -->
- [x] Implement `list` command logic and table formatting using `rich` <!-- id: 11 -->
- [x] Implement `milestone` command logic to tag runs <!-- id: 12 -->
- [x] Wire `judge` command to execute `ReJudge.rejudge_all` with target run outputs <!-- id: 13 -->
- [x] Validate `oneshot.py` passes ruff linting `ruff check src/gavel_ai/cli/commands/oneshot.py` <!-- id: 14 -->

## Partition: feat/oneshot-integration

- [x] Apply `@pytest.mark.unit` to all existing foundational tests in `tests/unit/` <!-- id: 20 -->
- [x] Create `tests/integration/test_oneshot_e2e.py` <!-- id: 21 -->
- [x] Write integration test bridging cli, processor, and result storage <!-- id: 22 -->
- [x] Validate tests pass using `pytest -m integration` <!-- id: 23 -->

## Initiative Boundary

- [ ] Open PR: initiative/oneshot-convergence-v1 -> master and await merge approval before continuing <!-- id: 100 -->
