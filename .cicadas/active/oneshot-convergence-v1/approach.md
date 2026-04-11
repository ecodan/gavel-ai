---
summary: "This document outlines the sequential implementation strategy for oneshot-convergence-v1. It breaks the work into three partitions: Core execution fixes (immutability and retries), CLI command implementations (judge, list, milestone), and Integration Testing validation."
phase: "approach"
when_to_load:
  - "When starting registered feature branches or reviewing partition scope, sequencing, and dependencies."
  - "When deciding what work can proceed in parallel and what must wait."
depends_on:
  - "prd.md"
  - "ux.md"
  - "tech-design.md"
modules:
  - "gavel_ai.cli.commands.oneshot"
  - "gavel_ai.processors"
  - "gavel_ai.core.executor"
  - "gavel_ai.judges.rejudge"
index:
  strategy: "## Strategy"
  partitions: "## Partitions (Feature Branches)"
  sequencing: "## Sequencing"
  migrations_compat: "## Migrations & Compat"
  risks: "## Risks & Mitigations"
  alternatives: "## Alternatives Considered"
next_section: "Strategy"
---

# Approach: oneshot-convergence-v1

## Strategy
This initiative will be executed sequentially to ensure stability. First, we will fix the core engine execution bugs to establish a stable foundation. Second, we will wire up the missing CLI commands to leverage the core logic. Finally, we will write end-to-end integration tests to lock down the behavior.

## Partitions (Feature Branches)

### Partition 1: Execution Fixes → `feat/oneshot-execution-fixes`
**Modules**: `gavel_ai.processors.scenario_processor`, `gavel_ai.processors.prompt_processor`, `gavel_ai.processors.closedbox_processor`, `gavel_ai.models.runtime`
**Scope**: Fix scenario mutation bugs, standardize retry logic, improve error handling, and add milestone to run metadata.
**Dependencies**: None

#### Artifact Type
library

#### How to Run
- start: `pytest tests/unit/test_scenario_processor.py tests/unit/test_prompt_processor.py tests/unit/test_closedbox_processor.py`
- ready-check: All tests in above paths pass

#### Acceptance Criteria
- [ ] ScenarioProcessor processes scenarios without modifying the input object dictionary
- [ ] PromptInputProcessor utilizes `retry_with_backoff` correctly
- [ ] ClosedBoxInputProcessor catches specific exceptions and provides detailed logs
- [ ] RunMetadata data model supports `milestone: bool` and `comment: Optional[str]`

#### Implementation Steps
1. Update `RunMetadata` in `gavel_ai.models.runtime`
2. Apply `model_copy(deep=True)` fix to `ScenarioProcessor`
3. Refactor `PromptInputProcessor` and `ClosedBoxInputProcessor`

### Partition 2: CLI Wiring → `feat/oneshot-cli-wiring`
**Modules**: `gavel_ai.cli.commands.oneshot`
**Scope**: Implement the business logic and UI for `judge`, `list`, and `milestone` commands in the OneShot CLI workflow.
**Dependencies**: Requires `feat/oneshot-execution-fixes` for updated Metadata models.

#### Artifact Type
cli

#### How to Run
- start: `python -m gavel_ai.cli.main oneshot --help`
- ready-check: Exit code 0 with expected stdout

#### Acceptance Criteria
- [ ] `gavel oneshot list` successfully outputs a table of runs
- [ ] `gavel oneshot milestone --run <id>` updates metadata successfully
- [ ] `gavel oneshot judge --run <id>` executes `ReJudge` service
- [ ] Code complexity in `oneshot.py` passes ruff linting (below 10)

#### Implementation Steps
1. Refactor `run` command into helper functions
2. Implement `list` formatting helpers and command
3. Implement `milestone` IO updates and command
4. Implement `judge` command integration

### Partition 3: Testing & Quality → `feat/oneshot-integration`
**Modules**: `tests/integration/`, `pytest` configuration
**Scope**: Apply test tags across the repository and implement a true E2E OneShot integration test.
**Dependencies**: Requires `feat/oneshot-cli-wiring` to test full paths.

#### Artifact Type
library

#### How to Run
- start: `pytest -m integration`
- ready-check: All tests pass

#### Acceptance Criteria
- [ ] Complete E2E execution tests pass using mock providers
- [ ] `pytest -m unit` runs only unit tests successfully
- [ ] `pytest -m integration` runs only integration tests successfully

#### Implementation Steps
1. Apply `@pytest.mark.unit` to all existing foundational tests
2. Create `tests/integration/test_oneshot_e2e.py`
3. Implement test cases for full scaffold → run → list → judge → report loop

## Sequencing

```mermaid
graph LR
    P1[Execution Fixes] --> P2[CLI Wiring]
    P2 --> P3[Testing & Quality]
```

### Partitions DAG

```yaml partitions
- name: feat/oneshot-execution-fixes
  modules: [gavel_ai.processors, gavel_ai.models.runtime]
  depends_on: []

- name: feat/oneshot-cli-wiring
  modules: [gavel_ai.cli.commands.oneshot]
  depends_on: [feat/oneshot-execution-fixes]

- name: feat/oneshot-integration
  modules: [tests]
  depends_on: [feat/oneshot-cli-wiring]
```

## Migrations & Compat
No breaking changes. Metadata model updates fall back to Pydantic defaults (False / None) for existing run data seamlessly.

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Extracting commands breaks current CLI functionality | Heavy reliance on existing tests before/after refactoring |

## Alternatives Considered
Fixing CLI first was considered, but execution bugs must be solved so any test or run correctly validates the state.
