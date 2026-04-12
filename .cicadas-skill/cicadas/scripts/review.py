# Copyright 2026 Cicadas Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Check the code review verdict for the current initiative.

Reads .cicadas/active/{initiative}/review.md and parses the verdict line.

Exit codes:
  0 — PASS or PASS WITH NOTES (safe to merge)
  1 — BLOCK (must resolve blocking findings before merging)
  2 — review.md not found or unparseable (run Code Review subagent first)
"""

import argparse
import re
import subprocess
from pathlib import Path

from utils import get_project_root, load_json

VERDICTS: set[str] = {"PASS", "PASS WITH NOTES", "BLOCK"}

# Order matters: match longest string first so "PASS WITH NOTES" beats "PASS"
_VERDICT_PATTERN: re.Pattern[str] = re.compile(r"\*\*Verdict:\s*(PASS WITH NOTES|BLOCK|PASS)\*\*")


def _current_branch(root: Path) -> str | None:
    try:
        out: str = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, text=True
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _initiative_for_branch(registry: dict, branch: str) -> str | None:
    entry: dict | None = registry.get("branches", {}).get(branch)
    return entry.get("initiative") if entry else None


def parse_verdict(text: str) -> str | None:
    """Return the verdict string from review.md content, or None if not found."""
    m: re.Match[str] | None = _VERDICT_PATTERN.search(text)
    return m.group(1) if m else None


def check_review(initiative: str | None = None) -> int:
    root: Path = get_project_root()
    registry: dict = load_json(root / ".cicadas" / "registry.json")

    if initiative is None:
        branch: str | None = _current_branch(root)
        if not branch:
            print("Not a git repository or detached HEAD.")
            return 2
        initiative = _initiative_for_branch(registry, branch)
        if not initiative:
            print(f"Branch '{branch}' is not registered in registry.json.")
            return 2

    review_path: Path = root / ".cicadas" / "active" / initiative / "review.md"
    if not review_path.exists():
        print(f"No review.md found for initiative '{initiative}'.")
        print(f"  Expected: {review_path}")
        print("  Run the Code Review subagent first (see emergence/code-review.md).")
        return 2

    text: str = review_path.read_text()
    verdict: str | None = parse_verdict(text)
    if not verdict:
        print(f"[WARN] Could not parse verdict from {review_path}.")
        print("  Expected a line like: **Verdict: PASS**")
        return 2

    print(f"Code review verdict for '{initiative}': {verdict}")
    if verdict == "BLOCK":
        print("  Resolve all Blocking findings before merging.")
        return 1
    if verdict == "PASS WITH NOTES":
        print("  Advisory findings present — review before merging.")
        return 0
    # PASS
    print("  No blocking findings.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check code review verdict for the current initiative")
    parser.add_argument(
        "--initiative", default=None, help="Initiative name (default: detected from current branch)"
    )
    args: argparse.Namespace = parser.parse_args()
    raise SystemExit(check_review(initiative=args.initiative))
