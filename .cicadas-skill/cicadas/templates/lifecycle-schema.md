# Lifecycle schema

Per-initiative lifecycle lives in `.cicadas/drafts/{name}/lifecycle.json` (before kickoff) and `.cicadas/active/{name}/lifecycle.json` (after kickoff). It is promoted with other specs and archived with the initiative.

## Format

- **initiative** (string): Initiative name; set when creating the file.
- **pr_boundaries** (object): At which boundaries to open a PR. All booleans.
  - `specs` — default `false`
  - `initiatives` — default `true`
  - `features` — default `true`
  - `tasks` — default `false`
- **steps** (array): Ordered list of steps. Each step:
  - `id` (string): Stable identifier.
  - `name` (string): Human-readable label.
  - `description` (string, optional): What to do.
  - `opens_pr` (boolean, optional): When true, this step implies opening a PR at that boundary.

Default template: `lifecycle-default.json` (contains `pr_boundaries` and `steps`; add `initiative` when writing).
