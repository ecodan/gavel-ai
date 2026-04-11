# Repo Context

- Repo mode candidate: `large-repo`
- Dominant languages: `python`, `json`, `markdown`
- Build systems: `python`
- Declared modules: `gavel-ai`
- Major code zones:
  - `src`
  - `src/gavel_ai`
- Build/test/runtime surfaces:
  - Build: `pyproject.toml`
  - Test: `tests`
  - Runtime: `pyproject.toml`, `src`, `src/gavel_ai`
- Seeded slices:
  - `src` -> `src`
  - `src-gavel_ai` -> `src/gavel_ai`
  - `_bmad` -> `_bmad`
- Routing note: Start with `src` and expand to neighboring areas only if needed.
