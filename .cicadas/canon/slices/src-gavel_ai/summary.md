## Purpose

Core logic of the Gavel-AI framework. This slice contains the business logic for evaluation workflows, judging mechanisms, storage abstractions, and the CLI presentation layer. Most feature development and bug fixes will touch this slice.

## Included Paths

- `src/gavel_ai/`

## Common Neighbor Slices

- `tests/`: Integration and unit tests for this core logic.
- `_bmad/`: Orchestration and dev-time infrastructure.

## First Files To Inspect

- `src/gavel_ai/core/executor.py`: The main orchestration hub.
- `src/gavel_ai/cli/main.py`: CLI entry point and command registration.
- `src/gavel_ai/storage/run_context.py`: Artifact lifecycle management.
