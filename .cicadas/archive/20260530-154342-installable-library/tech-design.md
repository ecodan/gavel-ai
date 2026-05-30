---
summary: "Three changes across two parallel partitions. Partition 1: (a) new gavel init command in cli/main.py writes .gavel/config.json with eval_root; (b) resolve_eval_root() in cli/common.py reads CLI flag → GAVEL_EVAL_ROOT → .gavel/config.json → .gavel/evaluations; (c) uninit warning in main callback; (d) propagate resolved root through all command modules. Partition 2: pyproject.toml packages.find + package-data. No core/storage changes."
phase: "tech"
when_to_load:
  - "When implementing eval-root routing or packaging changes."
  - "When checking whether changes conform to the agreed technical approach."
depends_on:
  - "prd.md"
modules:
  - "cli/commands/oneshot.py"
  - "cli/commands/conv.py"
  - "cli/commands/autotune.py"
  - "cli/common.py"
  - "pyproject.toml"
index:
  overview: "## Overview & Context"
  stack: "## Tech Stack & Dependencies"
  structure: "## Project / Module Structure"
  adrs: "## Architecture Decisions (ADRs)"
  data_models: "## Data Models"
  interfaces: "## API & Interface Design"
  conventions: "## Implementation Patterns & Conventions"
  security_performance: "## Security & Performance"
  implementation_sequence: "## Implementation Sequence"
next_section: "Implementation Sequence"
---

# Tech Design: Installable Library

## Progress

- [x] Overview & Context
- [x] Tech Stack & Dependencies
- [x] Project / Module Structure
- [x] Architecture Decisions (ADRs)
- [x] Data Models
- [x] API & Interface Design
- [x] Implementation Patterns & Conventions
- [x] Security & Performance
- [x] Implementation Sequence

---

## Overview & Context

Two independent, non-blocking changes:

**Change A — Init Command + Eval Root Routing**: Three sub-changes:

1. **`gavel init`**: New command in `cli/main.py` (registered on the root app). Prompts for eval root (default `./evals`), writes `.gavel/config.json = {"eval_root": "<path>"}`. Idempotent — warns and exits if config already exists (unless `--force`).

2. **`resolve_eval_root()`**: New helper in `cli/common.py`. Resolution chain: CLI flag arg → `GAVEL_EVAL_ROOT` env var (handled by Typer `envvar=`) → read `eval_root` from `.gavel/config.json` if present → fall back to `.gavel/evaluations`. Typer passes env var value as the string arg, so the function only needs to handle `None` → config.json → default.

3. **Uninit warning**: In `main.py`'s `@app.callback()`, after dotenv loading, check for `.gavel/config.json`. If absent, print one warning line via `typer.secho()` suggesting `gavel init`. Skip the warning when the invoked command IS `init`.

The `create` command in `oneshot.py` already has a `--eval-root` option; `run`, `judge`, `report`, and `list` do not. `conv.py` has a module-level `DEFAULT_EVAL_ROOT`; `autotune.py` commands are stubs.

**Change B — Packaging**: The `pyproject.toml` uses setuptools with a `src/` layout but has no explicit package-discovery config and no `package-data` declaration. More critically, Jinja2 templates in `src/gavel_ai/reporters/templates/` are non-Python files and WILL be excluded from the wheel unless explicitly declared.

### Cross-Cutting Concerns

1. **Backward compatibility** — The default eval root MUST remain `.gavel/evaluations` when no flag, env var, or config.json is present. No existing command invocation should change behavior.
2. **Single source of truth** — `resolve_eval_root()` in `common.py` is the only place that reads `GAVEL_EVAL_ROOT`, `.gavel/config.json`, and applies the default. Per-command duplication is forbidden.
3. **Soft warning, not a hard error** — Missing `config.json` is a warning only. Existing CI pipelines and gavel-in-repo users must not break.
4. **No core/storage changes** — `LocalFileSystemEvalContext`, `LocalRunContext`, and all storage abstractions are unchanged. Only the CLI presentation layer changes.

### Brownfield Notes

- `cli/commands/oneshot.py` defines `DEFAULT_EVAL_ROOT` at module level; it will be removed after `common.py` gets `resolve_eval_root()`.
- The `create` command already has `--eval-root` — update its body to call `resolve_eval_root()` instead of its inline `Path(eval_root) if eval_root else Path(DEFAULT_EVAL_ROOT)`.
- `conv.py` and `autotune.py` must be read to inventory how many commands hardcode the root.

---

## Tech Stack & Dependencies

No new dependencies. All changes use existing libraries.

| Category | Selection | Rationale |
|----------|-----------|-----------|
| **CLI** | Typer (existing) | Option declaration unchanged; just adding more `typer.Option` fields |
| **Env vars** | `os.environ` (stdlib) | No dotenv for this; `GAVEL_EVAL_ROOT` is a shell/CI env var, not a `.env` key |
| **Packaging** | setuptools (existing) | Explicit `packages.find` + `package-data` declarations in `pyproject.toml` |

**New dependencies introduced:** None.

---

## Project / Module Structure

Only modified files; no new files:

```
src/gavel_ai/
├── cli/
│   ├── common.py              # [MODIFIED] add resolve_eval_root(), read_project_config()
│   ├── main.py                # [MODIFIED] gavel init command + uninit warning in callback
│   ├── commands/
│   │   ├── oneshot.py         # [MODIFIED] --eval-root on run/judge/report/list; use resolve_eval_root()
│   │   ├── conv.py            # [MODIFIED] --eval-root on all commands; use resolve_eval_root()
│   │   └── autotune.py        # [MODIFIED] --eval-root on run/report if non-stub; use resolve_eval_root()
pyproject.toml                 # [MODIFIED] packages.find + package-data
```

**Key structural decisions:**
- `gavel init` is a command on the root `app` in `main.py`, not a sub-app — it is project-level, not workflow-level.
- `resolve_eval_root()` and `read_project_config()` live in `cli/common.py`.
- `DEFAULT_EVAL_ROOT` constant is removed from `oneshot.py` and `conv.py`; the default `".gavel/evaluations"` lives only inside `resolve_eval_root()`.

---

## Architecture Decisions (ADRs)

### ADR-1: `gavel init` on the root app, uninit warning in the root callback

**Decision:** Register `gavel init` directly on the root Typer `app` in `main.py` (not as a sub-app), and put the uninit warning check in the root `@app.callback()`.

**Rationale:** Init is project-level setup, not a workflow command — it doesn't belong under `oneshot`, `conv`, or `autotune`. The root callback fires on every invocation, making it the right place for the warning. The warning must know whether the current command IS `init` to suppress itself; this is cleanly done with `ctx.invoked_subcommand` in the callback.

**Affects:** `cli/main.py`.

---

### ADR-1b: Centralize resolution in `cli/common.py`, not `main.py` callback

**Decision:** Add `resolve_eval_root(eval_root_str: Optional[str]) -> Path` and `read_project_config() -> dict` to `cli/common.py` rather than threading a global through `main.py`'s Typer callback.

**Rationale:** Typer context threading between a parent app and mounted sub-apps requires `ctx.ensure_object(dict)` and `ctx: typer.Context` on every subcommand — significant boilerplate. A standalone helper function is simpler, testable in isolation, and consistent with how shared CLI utilities are already handled in `common.py`.

**Affects:** `cli/common.py`, all command files.

---

### ADR-2: Add `--eval-root` per-command, not as a global flag

**Decision:** Each command that touches the filesystem adds its own `--eval-root: Optional[str] = typer.Option(None, "--eval-root", envvar="GAVEL_EVAL_ROOT")` option.

**Rationale:** This is more explicit than global state and allows future commands to opt in naturally. Typer's `envvar=` parameter means the env var handling is also per-option, which auto-generates correct help text (`[env var: GAVEL_EVAL_ROOT]`). The `resolve_eval_root()` helper prevents duplication of the fallback logic.

**Affects:** `oneshot.py`, `conv.py`, `autotune.py`.

---

### ADR-3: Use Typer `envvar=` parameter rather than `os.environ.get()` in the function body

**Decision:** Declare `envvar="GAVEL_EVAL_ROOT"` on the Typer option itself instead of reading the env var inside `resolve_eval_root()`.

**Rationale:** When Typer's `envvar=` is set, the env var value is passed as the `eval_root_str` argument if the CLI flag is absent — the function body receives the resolved string and doesn't need to know about env vars at all. This means `resolve_eval_root()` only needs to handle `None` → default-path. Typer also shows the env var name in `--help` output automatically.

**Affects:** `cli/common.py` (simplified), all command options.

---

### ADR-4: Explicit `packages.find` and `package-data` in pyproject.toml

**Decision:** Add `[tool.setuptools.packages.find]` with `where = ["src"]` and `[tool.setuptools.package-data]` with `"gavel_ai" = ["reporters/templates/*"]`.

**Rationale:** Relying on setuptools auto-discovery without an explicit `where` is brittle — behavior varies between setuptools versions and build backends. Explicit declarations are deterministic and self-documenting. `package-data` is required for non-Python files (`.html` templates) to be included in the wheel.

**Affects:** `pyproject.toml`.

---

## Data Models

No model changes. `LocalFileSystemEvalContext` already accepts `eval_root: Path` — this initiative only changes what value is passed to it.

---

## API & Interface Design

### `gavel init` command — new in `cli/main.py`

```python
@app.command()
def init(
    eval_root: Optional[str] = typer.Option(None, "--eval-root", help="Eval root directory (default: ./evals)"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
) -> None:
    """Initialize gavel in the current project directory."""
    config_path = Path(".gavel") / "config.json"
    if config_path.exists() and not force:
        typer.secho("⚠ Already initialized. Use --force to overwrite.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)
    root = eval_root or typer.prompt("Eval root directory", default="./evals")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"eval_root": root}, indent=2))
    typer.secho(f"✅ Initialized. Eval root: {root}", fg=typer.colors.GREEN)
    typer.echo("   Next: gavel oneshot create --eval <name>")
```

### Uninit warning — in `cli/main.py` `@app.callback()`

```python
@app.callback()
def main(ctx: typer.Context, ...) -> None:
    load_dotenv(...)
    if ctx.invoked_subcommand != "init" and not Path(".gavel/config.json").exists():
        typer.secho(
            "⚠ Not initialized. Run `gavel init` to configure this project.",
            fg=typer.colors.YELLOW, err=True
        )
```

### `read_project_config()` and `resolve_eval_root()` — new in `cli/common.py`

```python
_DEFAULT_EVAL_ROOT = ".gavel/evaluations"
_PROJECT_CONFIG_PATH = Path(".gavel") / "config.json"

def read_project_config() -> dict:
    """Read .gavel/config.json; return {} if absent or unparseable."""
    try:
        return json.loads(_PROJECT_CONFIG_PATH.read_text()) if _PROJECT_CONFIG_PATH.exists() else {}
    except (json.JSONDecodeError, OSError):
        return {}

def resolve_eval_root(eval_root_str: Optional[str]) -> Path:
    """
    Resolution order: CLI flag → GAVEL_EVAL_ROOT env var (via Typer envvar=)
    → .gavel/config.json eval_root → .gavel/evaluations default.
    """
    if eval_root_str is not None:
        return Path(eval_root_str)
    config_root = read_project_config().get("eval_root")
    if config_root:
        return Path(config_root)
    return Path(_DEFAULT_EVAL_ROOT)
```

### Updated `_get_eval_dir()` signature in `oneshot.py`

```python
def _get_eval_dir(
    eval_name: Optional[str],
    run_id: Optional[str] = None,
    eval_root: Path = Path(".gavel/evaluations"),
) -> tuple[str, Path]:
    ...
```

### CLI option pattern (applied to each command)

```python
@app.command()
def run(
    eval_name: str = typer.Option(..., "--eval", help="Evaluation name"),
    eval_root: Optional[str] = typer.Option(
        None, "--eval-root", envvar="GAVEL_EVAL_ROOT",
        help="Root directory containing evaluations (default: .gavel/evaluations)",
    ),
) -> None:
    resolved_root = resolve_eval_root(eval_root)
    eval_ctx = LocalFileSystemEvalContext(eval_name=eval_name, eval_root=resolved_root)
    ...
```

### pyproject.toml additions

```toml
[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
gavel_ai = ["reporters/templates/*"]
```

### Backward Compatibility

Fully backward compatible. Callers who do not pass `--eval-root` and do not set `GAVEL_EVAL_ROOT` get exactly `.gavel/evaluations` — identical to today.

---

## Implementation Patterns & Conventions

- Follow existing `cli/common.py` pattern: pure functions, no side effects, importable without Typer context.
- `eval_root_str` is the string coming from Typer (may be `None`); `resolved_root` is always a `Path`.
- Do NOT call `resolved_root.mkdir()` in `resolve_eval_root()` — callers that need the dir to exist already handle that.
- Unit tests for `resolve_eval_root()`: test `None` → default, non-None string → `Path(string)`.
- No OTel spans needed — this is a trivial path resolution.

---

## Security & Performance

| Concern | Mitigation |
|---------|-----------|
| Path traversal via `--eval-root` | Not a concern; `--eval-root` is the root anchor, not a sub-path. OS enforces permissions. |
| Arbitrary path write | User controls where artifacts go — this is the intent. Same as today for the default path. |

No performance impact. `resolve_eval_root()` is a single string comparison + `Path()` constructor.

---

## Implementation Sequence

1. **`cli/common.py`** — add `resolve_eval_root()` and `_DEFAULT_EVAL_ROOT`. Remove `DEFAULT_EVAL_ROOT` from `oneshot.py`. *(Partition 1, blocking step)*
2. **`oneshot.py`** — update `_get_eval_dir()` signature; add `--eval-root` to `run`, `judge`, `report`, `list`; update `create` to use `resolve_eval_root()`. *(Partition 1)*
3. **`conv.py` + `autotune.py`** — same pattern as step 2. *(Partition 1, can run in parallel with step 2 once step 1 is done)*
4. **`pyproject.toml`** — add `packages.find` + `package-data`. *(Partition 2, fully independent)*
5. **Tests** — unit tests for `resolve_eval_root()`; verify packaging in a temp venv. *(Parallel with steps 2–4)*

**Parallel work opportunities:** Partition 2 (packaging) is fully independent of Partition 1 (routing) and can proceed simultaneously.
