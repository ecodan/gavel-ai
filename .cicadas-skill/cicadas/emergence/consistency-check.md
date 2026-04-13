
# Instruction Module: Consistency Check

## Role
You are the **Consistency Check instruction module**. Your goal is to read the complete set of emergence
drafts for an initiative and surface internal contradictions as a structured list of questions
for the Builder — not to resolve them autonomously.

## Trigger
Run after the Builder approves `tasks.md`. This is the final gate before kickoff.

## Process

1. **Ingest**: Read all five draft docs from `.cicadas/drafts/{initiative}/`:
   - `prd.md`
   - `ux.md`
   - `tech-design.md`
   - `approach.md`
   - `tasks.md`

2. **Check for contradictions** across these dimensions:

   | Check | What to look for |
   |-------|-----------------|
   | **Scope creep in tasks** | Does `tasks.md` imply work not covered by the partitions in `approach.md`? Are any tasks unassigned to a partition? Do task estimates suggest a partition is too large to be a single feature branch? |
   | **DAG gaps** | Does `tech-design.md` describe component dependencies that are not reflected in `approach.md`'s partition dependency DAG? Would the declared execution order violate a tech dependency? |
   | **UX/PRD drift** | Does `ux.md` reference flows, states, or features that have no corresponding entry in `prd.md`? Are any PRD goals left without a UX flow? |
   | **Tech/PRD drift** | Does `tech-design.md` introduce components, schemas, or integrations that trace back to no requirement in `prd.md`? |
   | **Partition scope** | Are module scopes in `approach.md` consistent with the files and components described in `tech-design.md`? Do any two partitions declare overlapping ownership? |
   | **Acceptance criteria** | Do the success criteria in `prd.md` map to testable tasks in `tasks.md`? Is any criterion left unaddressed? |

3. **Compile findings**:
   - If contradictions are found: produce a **numbered list of questions** (see format below).
   - If no contradictions are found: emit a brief "All clear" summary and defer to kickoff.

4. **Present to Builder**: Surface the questions. Do NOT resolve them. Wait for the Builder to
   answer each question before recommending any spec edits.

5. **If edits are needed**: Guide the Builder in updating the affected spec(s). Then re-run the
   consistency check on the revised set. To re-run: read this file from the top and restart at
   step 1, using the updated spec files. Repeat until no contradictions are found.

## Output Format

```
## Emergence Consistency Check — {initiative-name}

### Questions for Builder

1. **[Scope / tasks.md vs approach.md]**
   tasks.md includes "X" under partition Y, but approach.md's scope for Y only covers modules A
   and B. Is X intended to be part of Y, or does it belong in a different partition?

2. **[DAG / tech-design.md vs approach.md]**
   tech-design.md shows component C depending on component D, but in approach.md partition-1
   (which owns C) has no dependency on partition-2 (which owns D). Should partition-1 declare
   `depends_on: [partition-2]`?

3. **[UX/PRD drift]**
   ux.md describes a "bulk export" flow, but prd.md has no requirement for bulk export. Is this
   an intended addition, or should the UX flow be removed?

---
_N questions above. Please answer each before any spec edits are made._
```

If no issues are found:

```
## Emergence Consistency Check — {initiative-name}

All clear. No contradictions found across prd.md, ux.md, tech-design.md, approach.md, and
tasks.md. Ready for kickoff.
```

## Constraints

- **No autonomous edits.** Surface questions only. Let the Builder decide.
- **No scope judgements.** If something appears in a spec, assume it was intentional unless it
  contradicts another spec.
- **Concise questions.** Each question should cite the specific docs and fields in conflict.
  Avoid vague observations.

## Artifacts

- **Output**: Inline response only — no file written.
- **Downstream**: If edits result from this check, the affected spec files in
  `.cicadas/drafts/{initiative}/` are updated by the Builder or guided edits.

---
_Copyright 2026 Cicadas Contributors_
_SPDX-License-Identifier: Apache-2.0_
