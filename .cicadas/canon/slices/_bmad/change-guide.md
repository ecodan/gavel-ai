## Change Guide

### Adding a New Workflow

1. Determine the appropriate category under `_bmad/bmm/workflows/`.
2. Create `steps-c/`, `steps-e/`, and `steps-v/` folders for Create, Edit, and Validate logic respectively.
3. Define the `workflow.md` as the local orchestrator for that category.
4. Add the entry point command to `_bmad/core/agents/bmad-master.md`.
5. Create any required templates in the `templates/` folder.

### Modifying an Agent Persona

1. Identify the agent file in `_bmad/core/agents/`.
2. Update the system prompt instructions.
3. Run `python .cicadas-skill/cicadas/scripts/cicadas.py check` to ensure no cross-agent conflicts were introduced.

### Updating Documentation Requirements

1. Modify `_bmad/bmm/workflows/document-project/documentation-requirements.csv`.
2. Rerun the `/document` command to update the indices.
