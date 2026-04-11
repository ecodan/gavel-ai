## Purpose

Infrastructure for the **BMAD Management Methodology (BMM)**. This slice contains the "brain" of the project's management layer, including agent personas, workflow definitions, and the output of the planning process. It orchestrates the lifecycle from PRD discovery to implementation-readiness checks.

## Included Paths

- `_bmad/`: Methodology definitions, agents, and core workflows.
- `_bmad-output/`: Persistent planning artifacts (PRDs, Epics, Stories, Architecture).

## Common Neighbor Slices

- `src-gavel_ai`: The target codebase being managed by these workflows.

## First Files To Inspect

- `_bmad/core/agents/bmad-master.md`: The central orchestrator agent.
- `_bmad/bmm/workflows/`: The library of available engineering processes.
- `_bmad-output/planning-artifacts/`: The current state of the project's design.
