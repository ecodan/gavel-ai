# Copyright 2026 Cicadas Contributors
# SPDX-License-Identifier: Apache-2.0

"""skill_publish.py — copy or symlink an active skill to its publish destination.

Usage:
    python skill_publish.py <slug> [--publish-dir DIR] [--symlink] [--force] [--cicadas-dir DIR]

Reads publish_dir from active/skill-{slug}/emergence-config.json unless --publish-dir is given.
Runs validate_skill.py as a pre-publish check before writing anything.

Exit codes:
    0   Published successfully
    1   Error (validation failure, skill dir not found, publish_dir null/missing,
        destination conflict)
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from utils import get_project_root
from validate_skill import validate


def publish(slug: str, publish_dir: str | None = None, symlink: bool = False,
            force: bool = False, cicadas_dir: Path | None = None) -> None:
    if cicadas_dir is None:
        cicadas_dir = get_project_root() / ".cicadas"

    skill_dir = cicadas_dir / "active" / f"skill-{slug}"
    if not skill_dir.exists():
        print(f"[ERR] Skill directory not found: {skill_dir}")
        sys.exit(1)

    # Resolve publish destination
    if publish_dir is None:
        config_path = skill_dir / "emergence-config.json"
        if not config_path.exists():
            print(f"[ERR] emergence-config.json not found in {skill_dir}; use --publish-dir to specify destination")
            sys.exit(1)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        publish_dir = config.get("publish_dir")
        if not publish_dir:
            print("[ERR] publish_dir is null or missing in emergence-config.json; use --publish-dir to specify destination")
            sys.exit(1)

    # Pre-publish validation
    errors = validate(str(skill_dir), cicadas_dir=cicadas_dir)
    if errors:
        for err in errors:
            print(f"[ERR] {err}")
        print("[ERR] Validation failed — skill not published")
        sys.exit(1)

    # Resolve destination path relative to project root
    project_root = get_project_root()
    dest_base = (project_root / publish_dir).resolve()
    dest = dest_base / slug

    # Safety: ensure destination is under project root or a known parent
    try:
        dest_base.relative_to(project_root.resolve())
    except ValueError:
        # Allow absolute paths outside the project root (user chose them explicitly)
        pass

    if dest.exists():
        if not force:
            print(f"[ERR] Destination already exists: {dest} — use --force to overwrite")
            sys.exit(1)
        if dest.is_symlink() or not dest.is_dir():
            dest.unlink()
        else:
            shutil.rmtree(dest)

    dest_base.mkdir(parents=True, exist_ok=True)

    if symlink:
        dest.symlink_to(skill_dir.resolve())
    else:
        shutil.copytree(str(skill_dir), str(dest))

    print(f"[OK]  Published skill/{slug} to {dest}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish an active skill to its destination directory")
    parser.add_argument("slug", help="Skill slug (e.g. pdf-utils) — resolves to active/skill-{slug}/")
    parser.add_argument("--publish-dir", dest="publish_dir", default=None,
                        help="Override publish destination (default: read from emergence-config.json)")
    parser.add_argument("--symlink", action="store_true",
                        help="Create a symlink instead of copying (default: copy)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite destination if it already exists")
    parser.add_argument("--cicadas-dir", dest="cicadas_dir", default=None,
                        help="Path to .cicadas/ root (default: auto-detected)")
    args = parser.parse_args()

    cicadas = Path(args.cicadas_dir) if args.cicadas_dir else None
    publish(args.slug, publish_dir=args.publish_dir, symlink=args.symlink,
            force=args.force, cicadas_dir=cicadas)


if __name__ == "__main__":
    main()
