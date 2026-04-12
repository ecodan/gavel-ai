# Copyright 2026 Cicadas Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Create or update lifecycle.json for an initiative (drafts or active).
Loads default template and sets pr_boundaries from CLI flags.
Defaults: specs=no, initiatives=yes, features=yes, tasks=no.

After setting pr_boundaries, opens_pr is applied to the relevant steps:
  feature_work      → pr_boundaries.tasks
  complete_feature  → pr_boundaries.features
  complete_initiative → pr_boundaries.initiatives
"""

import argparse
from pathlib import Path

from utils import get_project_root, load_json, save_json

# Maps step id → the pr_boundaries key that controls whether that step opens a PR.
_STEP_BOUNDARY_MAP: dict[str, str] = {
    "feature_work": "tasks",
    "complete_feature": "features",
    "complete_initiative": "initiatives",
}


def _templates_dir() -> Path:
    """Directory containing lifecycle-default.json (sibling of scripts/)."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent / "templates"


def _apply_pr_to_steps(steps: list[dict], pr_boundaries: dict[str, bool]) -> list[dict]:
    """Set or remove opens_pr on each step based on its corresponding pr_boundary."""
    for step in steps:
        boundary: str | None = _STEP_BOUNDARY_MAP.get(step.get("id", ""))
        if boundary is not None:
            if pr_boundaries.get(boundary, False):
                step["opens_pr"] = True
            else:
                step.pop("opens_pr", None)
    return steps


def create_lifecycle(
    initiative_name: str,
    dest: str = "drafts",
    pr_specs: bool = False,
    pr_initiatives: bool = True,
    pr_features: bool = True,
    pr_tasks: bool = False,
) -> Path:
    root: Path = get_project_root()
    cicadas: Path = root / ".cicadas"
    templates: Path = _templates_dir()
    default_path: Path = templates / "lifecycle-default.json"

    if not default_path.exists():
        # Fallback: minimal default (no opens_pr; _apply_pr_to_steps will set them)
        data: dict = {
            "pr_boundaries": {"specs": False, "initiatives": True, "features": True, "tasks": False},
            "steps": [
                {
                    "id": "kickoff_initiative",
                    "name": "Kickoff initiative",
                    "description": "Promote drafts to active, create initiative branch",
                },
                {
                    "id": "kickoff_features",
                    "name": "Kickoff feature branches",
                    "description": "For each partition, run branch.py",
                },
                {
                    "id": "feature_work",
                    "name": "Feature work (per feature)",
                    "description": "Task branches → implement → test → reflect → commit → push → PR (if enabled) → merge to feature",
                },
                {
                    "id": "complete_feature",
                    "name": "Complete each feature",
                    "description": "Update index, push, open PR to initiative (if enabled), merge",
                },
                {
                    "id": "complete_initiative",
                    "name": "Complete initiative",
                    "description": "Open PR to main (if enabled), merge, synthesize canon, archive",
                },
            ],
        }
    else:
        data = load_json(default_path)

    data["initiative"] = initiative_name
    data["pr_boundaries"] = {
        "specs": pr_specs,
        "initiatives": pr_initiatives,
        "features": pr_features,
        "tasks": pr_tasks,
    }
    _apply_pr_to_steps(data.get("steps", []), data["pr_boundaries"])

    if dest == "active":
        out_dir: Path = cicadas / "active" / initiative_name
    else:
        out_dir = cicadas / "drafts" / initiative_name

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path: Path = out_dir / "lifecycle.json"
    save_json(out_path, data)
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create lifecycle.json for an initiative (drafts or active)")
    parser.add_argument("name", help="Initiative name")
    parser.add_argument("--active", action="store_true", help="Write to active/{name}/ instead of drafts/{name}/")
    parser.add_argument("--pr-specs", action="store_true", help="Open PR at specs boundary (default: no)")
    parser.add_argument("--pr-initiatives", action="store_true", default=True, help="Open PR at initiative→main (default: yes)")
    parser.add_argument("--no-pr-initiatives", action="store_false", dest="pr_initiatives", help="Do not open PR at initiative→main")
    parser.add_argument("--pr-features", action="store_true", default=True, help="Open PR at feature→initiative (default: yes)")
    parser.add_argument("--no-pr-features", action="store_false", dest="pr_features", help="Do not open PR at feature→initiative")
    parser.add_argument("--pr-tasks", action="store_true", help="Open PR at task→feature (default: no)")
    args = parser.parse_args()

    dest = "active" if args.active else "drafts"
    create_lifecycle(
        args.name,
        dest=dest,
        pr_specs=args.pr_specs,
        pr_initiatives=args.pr_initiatives,
        pr_features=args.pr_features,
        pr_tasks=args.pr_tasks,
    )
