---
summary: "Enable gavel-ai to be used as a library dependency in external Python projects via `uv add gavel-ai`. Three changes: (1) `gavel init` command creates .gavel/config.json with project-local eval root; (2) all CLI commands resolve eval root via flag → env var → config.json → default, with a warning on uninit'd projects; (3) pyproject.toml packaging fix for src/ layout and Jinja2 templates. Existing users see no behavioral change unless they opt in to init."
phase: "clarify"
when_to_load:
  - "When defining or reviewing initiative goals, users, scope, and success criteria."
  - "When validating that implementation aligns with the installable-library intent."
depends_on: []
modules:
  - "cli/commands/oneshot.py"
  - "cli/commands/conv.py"
  - "cli/commands/autotune.py"
  - "cli/common.py"
  - "cli/main.py"
  - "pyproject.toml"
index:
  executive_summary: "## Executive Summary"
  project_classification: "## Project Classification"
  success_criteria: "## Success Criteria"
  user_journeys: "## User Journeys"
  scope: "## Scope"
  functional_requirements: "## Functional Requirements"
  non_functional_requirements: "## Non-Functional Requirements"
  open_questions: "## Open Questions"
  risk_mitigation: "## Risk Mitigation"
next_section: "Risk Mitigation"
---

# PRD: Installable Library

## Progress

- [x] Executive Summary
- [x] Project Classification
- [x] Success Criteria
- [x] User Journeys
- [x] Scope & Phasing
- [x] Functional Requirements
- [x] Non-Functional Requirements
- [x] Open Questions
- [x] Risk Mitigation

## Executive Summary

Gavel-AI currently assumes it is run from within its own repository, with eval dirs at `.gavel/evaluations/` relative to the working directory. This makes it impossible to use as a dependency in another project. This initiative makes gavel a proper installable library: `uv add gavel-ai` works, the CLI accepts `--eval-root` to point at any directory, and all artifacts land where the caller specifies.

### What Makes This Special

- **Zero-friction adoption** — `gavel init` sets up a new project in one command; `uv add gavel-ai` + `gavel init` is the complete onboarding flow.
- **Eval-root portability** — a four-tier resolution chain (CLI flag → env var → `.gavel/config.json` → built-in default) means developers configure once and forget.
- **Full backward compatibility** — existing gavel-in-repo workflows are unaffected; `init` is opt-in and the built-in default is unchanged.

## Project Classification

**Technical Type:** Developer Tool / Library  
**Domain:** AI Evaluation Infrastructure  
**Complexity:** Low-Medium — three changes (init command + CLI routing + packaging hygiene); minimal new abstractions  
**Project Context:** Brownfield — new `gavel init` command, modifications to existing CLI commands and pyproject.toml

---

## Success Criteria

### User Success

A user achieves success when they can:

1. **Install and initialize** — `uv add gavel-ai` in a new project, then `gavel init` creates `.gavel/config.json` and prints next-steps guidance.
2. **Create and run an eval** — `gavel oneshot create --eval my-eval` (after init configures eval root) scaffolds the standard directory structure, and `gavel oneshot run --eval my-eval` produces run artifacts in the configured location.
3. **Warned on uninit'd project** — running any gavel command in a project where `gavel init` was never run prints a one-line warning suggesting `gavel init`.

### Technical Success

The system is successful when:

1. `pip install -e .` (and `uv add gavel-ai` from a path dependency) installs the package with all CLI commands and Jinja2 templates accessible.
2. All existing `pytest -m unit` and `pytest -m integration` tests continue to pass.
3. `gavel init` creates `.gavel/config.json` idempotently with the user-specified (or default) eval root.

### Measurable Outcomes

- `gavel init` creates `.gavel/config.json`; re-running it warns but does not overwrite.
- All commands in `gavel oneshot`, `gavel conv`, `gavel autotune` accept and respect `--eval-root`.
- Resolution order is enforced: CLI flag beats env var beats config.json beats built-in default.
- Running any command in an uninit'd directory emits exactly one warning line (not a hard error).
- `gavel` CLI entry point is discoverable after `pip install`.
- Jinja2 report templates are included in the installed package (no `FileNotFoundError` on `gavel oneshot report`).

---

## User Journeys

### Journey 1: App Developer Adding Evals to Their Project

Sarah is building a RAG application. She wants to run quality evals against her prompts without managing a separate gavel repo. She adds `gavel-ai` to her project's `pyproject.toml` dev dependencies and runs `gavel init`. Init prompts her for an eval root (she types `./evals`) and writes `.gavel/config.json`. She runs `gavel oneshot create --eval quality-check`, fills in her scenarios, and runs `gavel oneshot run --eval quality-check` — artifacts land in `./evals/quality-check/runs/` automatically. On her next project, she runs `gavel init` again and is up and running in 60 seconds.

**Requirements Revealed:** `gavel init` command, config.json eval root storage, create/run/report respecting stored root, working install from external project.

### Journey 2: CI Pipeline Running Evals on Each PR

A team's CI workflow checks out their app repo, installs dependencies including `gavel-ai`, and runs `GAVEL_EVAL_ROOT=./evals gavel oneshot run --eval quality-check` to gate PRs. The artifacts land in the workspace and are uploaded as CI artifacts. No gavel source code is checked out; everything comes from the installed package.

**Requirements Revealed:** Installed package includes templates, no dependency on gavel source tree at runtime.

### Journey Requirements Summary

| User Type | Key Requirements |
|-----------|-----------------|
| **App Developer** | `gavel init`, config.json root storage, clean install, create/run/report respect stored root, `--eval-root` override |
| **CI Pipeline** | Package includes templates, no source-tree dependency, `GAVEL_EVAL_ROOT` or `--eval-root` override |

---

## Scope

### MVP — Minimum Viable Product (v1)

**Core Deliverables:**
- `gavel init` command: interactive prompt for eval root, writes `.gavel/config.json`, idempotent (warns if already initialized)
- Per-command eval root resolution: CLI flag → `GAVEL_EVAL_ROOT` env var → `.gavel/config.json` → `.gavel/evaluations` default
- One-line warning on any command invocation when `.gavel/config.json` is absent (soft warning, not a hard error)
- `--eval-root` option on all `gavel oneshot`, `gavel conv`, and `gavel autotune` commands (explicit per-invocation override)
- `pyproject.toml` packaging fix: `[tool.setuptools.packages.find]` with `where = ["src"]`
- `[tool.setuptools.package-data]` to include Jinja2 templates in the installed package
- Smoke test verifying install + `gavel --help` in a temporary venv

**Quality Gates:**
- All existing unit and integration tests pass
- Manual verification: `pip install -e .` in a fresh venv, `gavel init`, create + run an eval from a different working directory

### Growth Features (Post-MVP)

**v2: Python API**
- Programmatic invocation (`from gavel_ai import run_eval(...)`) without subprocess/CLI
- Useful for embedding evals in pytest suites

**v3: Published to PyPI**
- `uv add gavel-ai` from PyPI (not just local path)
- Versioned releases, changelog

### Vision (Future)

- Plugin hooks for custom reporters, judges, and providers loadable from installed packages

---

## Functional Requirements

### 1. Project Initialization (`gavel init`)

**FR-1.1:** `gavel init` MUST create `.gavel/config.json` in the current working directory with at minimum an `eval_root` field.
- Must prompt the user for eval root (default: `./evals`) unless `--eval-root` is passed non-interactively
- Must print a success message with next-step guidance after writing the file

**FR-1.2:** `gavel init` MUST be idempotent: if `.gavel/config.json` already exists, warn the user and exit without overwriting. A `--force` flag overrides this.

**FR-1.3:** Running any `gavel` command (except `gavel init` itself) when `.gavel/config.json` does not exist in the current directory MUST print a single soft warning line suggesting `gavel init`. This MUST NOT block execution.

### 2. Eval Root Configuration

**FR-2.1:** Every command that reads or writes eval artifacts MUST resolve eval root using the following priority chain, highest to lowest:
1. `--eval-root <path>` CLI flag (explicit per-invocation override)
2. `GAVEL_EVAL_ROOT` environment variable
3. `eval_root` field from `.gavel/config.json` in the current working directory
4. Built-in default: `.gavel/evaluations`

**FR-2.2:** The resolution logic MUST live in a single helper (`resolve_eval_root()` in `cli/common.py`). Per-command duplication is forbidden.

**FR-2.3:** The `create` command's existing `--eval-root` option MUST be updated to use the shared resolution helper (currently it ignores the env var and config.json).

### 3. Package Installability

**FR-3.1:** The installed package MUST include Jinja2 HTML templates from `src/gavel_ai/reporters/templates/` so that `gavel oneshot report` works without the source tree.
- `pyproject.toml` MUST declare `[tool.setuptools.package-data]` covering `reporters/templates/*`

**FR-3.2:** `pyproject.toml` MUST explicitly configure `[tool.setuptools.packages.find]` with `where = ["src"]`.

**FR-3.3:** After `pip install -e .` (or `pip install .`) in an isolated venv, `gavel --help` MUST print help text and exit 0 with no import errors.

---

## Non-Functional Requirements

- **Performance:** No change to execution performance. `resolve_eval_root()` is a trivial string/Path operation.
- **Reliability:** Default behavior (`.gavel/evaluations`) is strictly preserved when neither `--eval-root` nor `GAVEL_EVAL_ROOT` is set.
- **Security:** `--eval-root` accepts any filesystem path; no path traversal restriction needed (it's the root, not a sub-path). Paths are passed as-is to `Path()`; the OS enforces access control.
- **Maintainability:** Eval root resolution centralized in one function. Adding a new command requires only adding `eval_root` as a parameter and calling `resolve_eval_root()`.

---

## Open Questions

- **PyPI publication**: Should this initiative also publish to PyPI, or is local `pip install -e .` / path-dependency sufficient for MVP? (Recommendation: defer PyPI to v2; it requires versioning, token management, and release process decisions.)
- **`conv` and `autotune` scope**: How many commands in `conv` and `autotune` currently hardcode the eval root? (Answer: to be confirmed during tech design by reading those files.)

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| setuptools `src/` auto-discovery already works | Medium | Low | Verify in tech design by checking current `pip install -e .` behavior; if it works, FR-2.2 is a no-op confirmation |
| `--eval-root` conflicts with existing `create` option | Low | Low | The `create` command already has `--eval-root`; we're updating it to use the shared helper, not adding a duplicate |
| Template files already included via `MANIFEST.in` or auto-include | Low | Low | Check packaging artifacts in tech design; add explicit `package-data` regardless for clarity |
