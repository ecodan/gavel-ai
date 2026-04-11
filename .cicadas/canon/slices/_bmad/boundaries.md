## Input Boundaries

- **User Directives**: Natural language requests often prefixed with slash commands (e.g., `/prd`).
- **Project Pulse**: The current state of the `src/` directory and `tests/`.
- **Workflow State**: Temporary progress markers in `_bmad/bmm/workflows/`.

## Output Boundaries

- **Planning Artifacts**: PRDs, Architecture Decision Documents, Epics & Stories stored in `_bmad-output/planning-artifacts/`.
- **Implementation Status**: Task lists and sprint logs stored in `_bmad-output/implementation-artifacts/`.
- **Agent Reasoning**: Ephemeral thought processes and dialogue between specialized agents (Master, Architect, PM, Dev).

## Public Interface

- **Slash Commands**: A set of standardized entry points into the methodology (PRD, ARCH, EPIC, STORY, DEPLOY).
- **Artifact Links**: Stable file paths in `_bmad-output/` that other agents can reference for context.
