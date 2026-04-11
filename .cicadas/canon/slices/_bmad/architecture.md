## Methodology Architecture

The BMM logic is built on **Modular Spec Engineering**. It is not a monolithic script but a series of interconnected Markdown and JSON instructions that guide multi-agent interactions.

### Component Map

- **Master Orchestrator**: The logic in `_bmad/core/agents/bmad-master.md` that routes user intent to the correct workflow.
- **Workflow Steps**: Granular, phase-based instructions (e.g., `_bmad/bmm/workflows/2-plan-workflows/prd/steps-c/`) that ensure consistent data gathering and validation.
- **Templates**: Standardized Markdown structures in `templates/` folders that define the expected output format for all design artifacts.
- **Validation Engine**: Specialized "steps-v" instructions that perform adversarial reviews of generated artifacts before completion.

### Integration with Development

The methodology output (`_bmad-output/`) serves as the input for implementation agents. While Cicadas manages the source-of-truth **Canon**, BMM manages the **Inclusion/Evolution** of that truth through its PRD and Architecture workflows.
