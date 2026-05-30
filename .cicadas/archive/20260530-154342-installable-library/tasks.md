---
summary: "Two parallel partitions. feat/eval-root-routing: gavel init command in main.py, read_project_config()+resolve_eval_root() in common.py, uninit warning in main callback, propagate --eval-root through oneshot/conv/autotune. feat/packaging-fix: packages.find + package-data in pyproject.toml + install verification. No PRs; merge directly to initiative branch."
phase: "tasks"
when_to_load:
  - "When selecting the next implementation task or reviewing completion state."
  - "When checking partition progress or execution sequencing."
depends_on:
  - "prd.md"
  - "tech-design.md"
  - "approach.md"
modules:
  - "cli/main.py"
  - "cli/common.py"
  - "cli/commands/oneshot.py"
  - "cli/commands/conv.py"
  - "cli/commands/autotune.py"
  - "pyproject.toml"
index:
  partition_routing: "## Partition: feat/eval-root-routing"
  partition_packaging: "## Partition: feat/packaging-fix"
  initiative_boundary: "## Initiative Boundary"
next_section: "## Partition: feat/eval-root-routing"
---

# Tasks: Installable Library

## Partition: feat/eval-root-routing

- [ ] Read `src/gavel_ai/cli/common.py` to confirm it has no existing `resolve_eval_root`; read `src/gavel_ai/cli/commands/conv.py` and `src/gavel_ai/cli/commands/autotune.py` to inventory all hardcoded eval root usages <!-- id: 1 -->
- [ ] Add `read_project_config() -> dict` to `src/gavel_ai/cli/common.py`: reads `.gavel/config.json` from CWD, returns `{}` on missing or unparseable file; import `json` and `Path` as needed <!-- id: 2 -->
- [ ] Add `_DEFAULT_EVAL_ROOT: str = ".gavel/evaluations"` and `resolve_eval_root(eval_root_str: Optional[str]) -> Path` to `src/gavel_ai/cli/common.py`: CLI flag arg → config.json `eval_root` → default <!-- id: 3 -->
- [ ] Add unit tests in `tests/unit/cli/test_common.py` (create file if absent): `resolve_eval_root(None)` with no config → default; `resolve_eval_root(None)` with config.json present → config value; `resolve_eval_root("/tmp/x")` → `Path("/tmp/x")` <!-- id: 4 -->
- [ ] Add `gavel init` command to `src/gavel_ai/cli/main.py`: accepts `--eval-root` (prompts if absent), writes `.gavel/config.json`, warns and exits 0 if already exists (unless `--force`); print next-steps guidance on success <!-- id: 5 -->
- [ ] Add uninit warning to `@app.callback()` in `main.py`: if `ctx.invoked_subcommand != "init"` and `.gavel/config.json` absent, `typer.secho()` a one-line warning to stderr — do NOT raise Exit <!-- id: 6 -->
- [ ] In `src/gavel_ai/cli/commands/oneshot.py`: remove `DEFAULT_EVAL_ROOT` constant; update `_get_eval_dir(eval_name, run_id=None, eval_root=Path(".gavel/evaluations"))` to use `eval_root` parameter <!-- id: 7 -->
- [ ] In `oneshot.py` `create` command: replace inline path logic with `resolve_eval_root(eval_root)`; add `envvar="GAVEL_EVAL_ROOT"` to existing `--eval-root` typer.Option <!-- id: 8 -->
- [ ] In `oneshot.py` `run` command: add `eval_root: Optional[str] = typer.Option(None, "--eval-root", envvar="GAVEL_EVAL_ROOT")` parameter; replace `DEFAULT_EVAL_ROOT` with `resolve_eval_root(eval_root)` in `LocalFileSystemEvalContext` call <!-- id: 9 -->
- [ ] In `oneshot.py` `judge`, `report`, `list` commands: add `--eval-root` option with `envvar="GAVEL_EVAL_ROOT"`; pass `resolve_eval_root(eval_root)` to `_get_eval_dir()` and `LocalFileSystemEvalContext` <!-- id: 10 -->
- [ ] In `src/gavel_ai/cli/commands/conv.py`: remove `DEFAULT_EVAL_ROOT` constant; add `--eval-root` with `envvar="GAVEL_EVAL_ROOT"` to `generate` command (and any other non-stub commands); replace hardcoded root with `resolve_eval_root(eval_root)` <!-- id: 11 -->
- [ ] In `src/gavel_ai/cli/commands/autotune.py`: add `--eval-root` to `run` and `report` if they reference eval dirs; skip if still stubs <!-- id: 12 -->
- [ ] Run `uv run pytest -m unit` and `uv run pytest -m integration` and confirm no regressions <!-- id: 13 -->
- [ ] Smoke test: run `gavel` in a directory with no `.gavel/config.json` — confirm one-line warning appears; run `gavel init --eval-root /tmp/gavel-test` — confirm `.gavel/config.json` created; run `gavel oneshot run --help` — confirm `--eval-root [env var: GAVEL_EVAL_ROOT]` in output <!-- id: 14 -->

## Partition: feat/packaging-fix

- [ ] Read `pyproject.toml` to confirm there is no existing `[tool.setuptools.packages.find]` or `[tool.setuptools.package-data]` section <!-- id: 20 -->
- [ ] Add to `pyproject.toml`: `[tool.setuptools.packages.find]` with `where = ["src"]` <!-- id: 21 -->
- [ ] Add to `pyproject.toml`: `[tool.setuptools.package-data]` with `"gavel_ai" = ["reporters/templates/*"]` <!-- id: 22 -->
- [ ] Create a temp venv and verify install: `python -m venv /tmp/gavel-venv && /tmp/gavel-venv/bin/pip install -e . && /tmp/gavel-venv/bin/gavel --help` — confirm exit 0 <!-- id: 23 -->
- [ ] Verify templates are included: in the temp venv, confirm `src/gavel_ai/reporters/templates/oneshot.html` is accessible (list the installed package's template files or run `gavel oneshot report` against an existing run if one exists) <!-- id: 24 -->
- [ ] Run `uv run pytest -m unit` after pyproject.toml changes to confirm no regressions <!-- id: 25 -->

## Initiative Boundary

- [ ] Merge `feat/eval-root-routing` into `initiative/installable-library` <!-- id: 100 -->
- [ ] Merge `feat/packaging-fix` into `initiative/installable-library` <!-- id: 101 -->
- [ ] Merge `initiative/installable-library` into `master` <!-- id: 102 -->
- [ ] Synthesize canon on `master` and archive `installable-library` <!-- id: 103 -->
