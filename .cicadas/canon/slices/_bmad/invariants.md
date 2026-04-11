## Methodology Invariants

1. **Step-by-Step Discovery**: No workflow may jump directly to final artifact generation. All workflows must proceed through discovery, drafting, and validation phases.
2. **Adversarial Validation**: Every major artifact (PRD, Architecture, Epic) must pass a validation check by a specialized "adversarial" agent role before being marked complete.
3. **Traceability**: All Epics must link back to a requirement in a PRD, and all Stories must link back to an Epic.
4. **Artifact Immobility**: Completed artifacts in `_bmad-output/` must not be manually edited; they should be updated via the "Edit" entry points of the relevant workflows.
