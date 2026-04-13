# Copyright 2026 Cicadas Contributors
# SPDX-License-Identifier: Apache-2.0

"""validate_skill.py — check an Agent Skill directory against the spec.

Usage:
    python validate_skill.py <path_or_slug> [--cicadas-dir DIR]

Resolves a slug to active/skill-{slug}/ first, then drafts/skill-{slug}/.
An explicit path is used as-is.

Exit codes:
    0   All checks passed
    1   One or more checks failed (errors printed to stdout)
"""

import argparse
import re
import sys
from pathlib import Path

from utils import get_project_root, load_json


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FIELD_RE = re.compile(r"^(\w[\w-]*):\s*(.*)", re.MULTILINE)
# Block scalar — value on following indented lines
_BLOCK_SCALAR_RE = re.compile(r"^(\w[\w-]*):\s*[|>][^\n]*\n((?:[ \t]+[^\n]*\n?)*)", re.MULTILINE)
# Name constraints per Agent Skills spec
_NAME_CHARSET_RE = re.compile(r"^[a-z0-9-]+$")


def _extract_frontmatter(text: str) -> dict[str, str] | None:
    """Return a dict of frontmatter key→value strings, or None if no frontmatter found."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    block = m.group(1)
    fields: dict[str, str] = {}

    # Block scalars first (|, >) — multi-line values
    for bm in _BLOCK_SCALAR_RE.finditer(block):
        key = bm.group(1)
        raw_lines = bm.group(2)
        # Strip common leading indentation and join
        lines = [ln.strip() for ln in raw_lines.splitlines() if ln.strip()]
        fields[key] = " ".join(lines)

    # Inline scalar fields (key: value on the same line)
    for fm in _FIELD_RE.finditer(block):
        key = fm.group(1)
        if key in fields:
            continue  # already captured as block scalar
        value = fm.group(2).strip().strip('"\'')
        fields[key] = value

    return fields


def _resolve_skill_dir(path_or_slug: str, cicadas: Path) -> Path:
    """Resolve a slug or explicit path to an absolute Path."""
    p = Path(path_or_slug)
    if p.is_absolute() or p.exists():
        return p.resolve()
    # Slug resolution: active first, then drafts
    for subdir in ("active", "drafts"):
        candidate = cicadas / subdir / f"skill-{path_or_slug}"
        if candidate.exists():
            return candidate
    # Return the active candidate even if it doesn't exist; validate will emit the error
    return cicadas / "active" / f"skill-{path_or_slug}"


def validate(path_or_slug: str, cicadas_dir: Path | None = None) -> list[str]:
    """Run all checks; return a list of error strings (empty = valid)."""
    if cicadas_dir is None:
        cicadas_dir = get_project_root() / ".cicadas"

    skill_dir = _resolve_skill_dir(path_or_slug, cicadas_dir)
    errors: list[str] = []

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append(f"SKILL.md not found in {skill_dir}")
        return errors  # nothing else to check

    text = skill_md.read_text(encoding="utf-8")
    fields = _extract_frontmatter(text)

    if fields is None:
        errors.append("No YAML frontmatter found (missing --- delimiters)")
        return errors  # can't check fields

    # --- name checks ---
    name = fields.get("name", "").strip()
    if not name:
        errors.append("'name' field missing from frontmatter")
    else:
        if len(name) > 64:
            errors.append(f"'name' value \"{name}\" exceeds 64 characters")
        if not _NAME_CHARSET_RE.match(name):
            errors.append(f"'name' value \"{name}\" contains invalid characters (allowed: a-z, 0-9, hyphens)")
        else:
            if name.startswith("-") or name.endswith("-"):
                errors.append(f"'name' value \"{name}\" starts or ends with a hyphen")
            if "--" in name:
                errors.append(f"'name' value \"{name}\" contains consecutive hyphens")

        # Directory match: strip skill- prefix from dir name to get expected slug
        dir_slug = skill_dir.name
        if dir_slug.startswith("skill-"):
            dir_slug = dir_slug[len("skill-"):]
        if name != dir_slug:
            errors.append(f"'name' value \"{name}\" does not match directory name \"{skill_dir.name}\"")

    # --- description checks ---
    description = fields.get("description", "")
    if "description" not in fields:
        errors.append("'description' field missing from frontmatter")
    elif not description.strip():
        errors.append("'description' is empty")
    elif len(description) > 1024:
        errors.append(f"'description' exceeds 1024 characters ({len(description)} chars)")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an Agent Skill directory against the spec")
    parser.add_argument("path_or_slug", help="Explicit path to skill dir, or a slug (e.g. pdf-utils)")
    parser.add_argument("--cicadas-dir", dest="cicadas_dir", default=None,
                        help="Path to .cicadas/ root (default: auto-detected)")
    args = parser.parse_args()

    cicadas = Path(args.cicadas_dir) if args.cicadas_dir else None
    errors = validate(args.path_or_slug, cicadas_dir=cicadas)

    if errors:
        for err in errors:
            print(f"[ERR] {err}")
        sys.exit(1)
    else:
        # Derive name for output
        skill_dir = _resolve_skill_dir(args.path_or_slug, cicadas or (get_project_root() / ".cicadas"))
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fields = _extract_frontmatter(text) or {}
        name = fields.get("name", args.path_or_slug)
        print(f"[OK]  skill/{name} is valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
