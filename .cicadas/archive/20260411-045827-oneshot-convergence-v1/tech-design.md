---
summary: "This tech design outlines the architectural refinements and wiring required for the oneshot-convergence-v1 initiative. It focuses on resolving technical debt in the processor layer (immutability, standardized retry) and implementing the CLI commands for judging, listing, and milestone management by wiring existing backend services (ReJudge, ResultStorage) to theTyper entry point."
phase: "tech"
when_to_load:
  - "When implementing or reviewing architecture, interfaces, data models, conventions, and sequencing."
  - "When checking whether changes still conform to the agreed technical approach."
depends_on:
  - "prd.md"
  - "ux.md"
modules:
  - "gavel_ai.cli.commands.oneshot"
  - "gavel_ai.processors.scenario_processor"
  - "gavel_ai.processors.prompt_processor"
  - "gavel_ai.judges.rejudge"
index:
  overview: "## Overview & Context"
  stack: "## Tech Stack & Dependencies"
  structure: "## Project / Module Structure"
  adrs: "## Architecture Decisions (ADRs)"
  data_models: "## Data Models"
  interfaces: "## API & Interface Design"
  conventions: "## Implementation Patterns & Conventions"
  security_performance: "## Security & Performance"
  implementation_sequence: "## Implementation Sequence"
next_section: "Overview & Context"
---

# Tech Design: oneshot-convergence-v1

## Progress

- [x] Overview & Context
- [x] Tech Stack & Dependencies
- [x] Project / Module Structure
- [x] Architecture Decisions (ADRs)
- [x] Data Models
- [x] API & Interface Design
- [x] Implementation Patterns & Conventions
- [x] Security & Performance
- [x] Implementation Sequence

---

## Overview & Context

**Summary:** This initiative resolves critical technical debt while completing the OneShot lifecycle. The primary architectural pattern is **Service Injection into CLI**: wiring existing core services like `ReJudge` and `ResultStorage` into the Typer-based presentation layer. Additionally, we enforce **Process Immutability** in the core layer to prevent side-effect bugs during multi-variant execution.

### Cross-Cutting Concerns

1. **Immutability** — Scenario objects must be treated as read-only throughout the execution pipeline.
2. **Error Recovery** — CLI commands must survive individual failures in `results.jsonl` lines.
3. **Complexity Control** — Typer commands must be kept lean by extracting business logic to helper functions.

---

## Tech Stack & Dependencies

| Category | Selection | Rationale |
|----------|-----------|-----------|
| **CLI Framework** | Typer | Existing project standard |
| **Data Handling** | Pydantic v2 | Existing project standard for models |
| **Storage** | JSONL (ResultStorage)| Existing project standard |
| **Async** | asyncio | Core execution requirement |

---

## Project / Module Structure

```
src/gavel_ai/
├── cli/
│   └── commands/
│       └── oneshot.py        # [MODIFIED] Implement judge, list, milestone
├── core/
│   └── retry.py              # Centralized retry-with-backoff
├── processors/
│   ├── prompt_processor.py   # [MODIFIED] Use core/retry
│   ├── scenario_processor.py # [MODIFIED] Implement deepcopy fix
│   └── closedbox_processor.py # [MODIFIED] Specific exception handling
└── judges/
    └── rejudge.py            # [MODIFIED] Ensure compatibility with CLI wiring
```

---

## Architecture Decisions (ADRs)

### ADR-1: Scenario Copy Selection

**Decision:** Use `input_item.model_copy(deep=True)` at the start of `ScenarioProcessor.process_async()`.

**Rationale:** This is the most efficient Pydantic-native way to ensure that any metadata mutation (like `conversation_history`) does not affect the original input scenario, preventing state leakage between variants.

**Affects:** `src/gavel_ai/processors/scenario_processor.py`

### ADR-2: OneShot CLI Refactoring

**Decision:** Extract all workflow orchestration logic from `oneshot.py` commands into private helper functions (e.g., `_load_eval_context`, `_render_run_table`).

**Rationale:** The `run()` command already exceeds cyclomatic complexity limits (C901). Modularizing the commands ensures they remain maintainable and pass linting.

**Affects:** `src/gavel_ai/cli/commands/oneshot.py`

---

## Data Models

### Modified Models

| Model | Change | Migration Required? |
|-------|--------|-------------------|
| `RunMetadata` | Add `milestone: bool = False`, `comment: Optional[str] = None` | No (Pydantic defaults) |

---

## API & Interface Design

### New CLI Commands

```bash
gavel oneshot judge --run <run-id> [--eval <eval-name>] [--judges J1,J2]
gavel oneshot list [--eval <eval-name>]
gavel oneshot milestone --run <run-id> [--eval <eval-name>] [--comment "..." ] [--remove]
```

---

## Performance & Security

- **Observability**: All re-judging operations must emit OTel spans for visibility into execution time.
- **Security**: CLI inputs (eval names, run IDs) must be sanitized to prevent path traversal issues.

---

## Implementation Sequence

1. **Foundation**: Update `RunMetadata` model and fix `ScenarioProcessor` mutation bug.
2. **Refactor**: Split `oneshot.py` into manageable helper functions.
3. **Core Wiring**: Implement `oneshot judge` using the `ReJudge` service.
4. **History Wiring**: Implement `oneshot list` and `oneshot milestone`.
5. **Testing**: Automate test tagging and add the end-to-end integration test.
