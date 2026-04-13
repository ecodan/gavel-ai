---
summary: "N/A — Backend Only. No user-facing UI changes."
phase: "ux"
when_to_load:
  - "Not needed — backend-only initiative."
depends_on:
  - "prd.md"
modules: []
---

# UX: judge-dry-fix

## Progress

- [x] UX Assessment

---

## N/A — Backend Only

This initiative is a pure pipeline refactor. All changes are internal to the oneshot judge pipeline:

- No new CLI commands or flags (the `--judges` filter option may be removed, which is a CLI simplification, not a new UX surface)
- No changes to output file formats (`results_raw.jsonl`, `results_judged.jsonl`, `manifest.json`, `report.html`)
- No new configuration schema
- No new user-visible behaviour beyond multi-variant evals now producing correct results (a bug fix)

No UX design work required.
