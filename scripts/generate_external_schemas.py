"""
Generate JSON Schema files for the external-runner protocol payload shapes.

Design decision: HTTP and script transports share the same Pydantic model shapes —
the payload contents are identical regardless of transport; only the delivery mechanism
differs (HTTP POST body vs. temp-dir request.json file). Therefore:

  - ExternalTaskRequest  → used for both HTTP task requests AND script task requests
  - ExternalJudgeRequest → used for both HTTP judge requests AND script judge requests
  - ExternalResponseEnvelope → used for ALL four response shapes (HTTP task, HTTP judge,
                                script task, script judge)

This script generates three JSON Schema files (one per distinct model) and documents
the eight transport-specific shapes in docs/specs/schema-external-runner.md.

Usage:
    uv run python scripts/generate_external_schemas.py
"""

import json
import sys
from pathlib import Path

# Add src to path so the script is runnable from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gavel_ai.models.runtime import (  # noqa: E402
    ExternalJudgeRequest,
    ExternalResponseEnvelope,
    ExternalTaskRequest,
)

OUTPUT_DIR: Path = Path(__file__).parent.parent / "docs" / "specs" / "schemas"

# Each entry: (filename_stem, model_class, description)
SCHEMA_TARGETS: list[tuple[str, type, str]] = [
    (
        "external_task_request",
        ExternalTaskRequest,
        (
            "Request payload for external task execution — used by both the HTTP transport "
            "(POST body) and the script transport (written to request.json in the temp dir)."
        ),
    ),
    (
        "external_judge_request",
        ExternalJudgeRequest,
        (
            "Request payload for external judge execution — used by both the HTTP transport "
            "(POST body) and the script transport (written to request.json in the temp dir)."
        ),
    ),
    (
        "external_response_envelope",
        ExternalResponseEnvelope,
        (
            "Response payload for all external execution shapes — used by both transports "
            "(HTTP response body / script response.json) for both task and judge responses."
        ),
    ),
]


def generate_schemas() -> dict[str, dict]:
    """Generate and return JSON schemas keyed by filename stem."""
    schemas: dict[str, dict] = {}
    for stem, model_cls, description in SCHEMA_TARGETS:
        schema: dict = model_cls.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["description"] = description
        schemas[stem] = schema
    return schemas


def write_schemas(schemas: dict[str, dict]) -> None:
    """Write schema dicts to OUTPUT_DIR as JSON files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for stem, schema in schemas.items():
        out_path: Path = OUTPUT_DIR / f"{stem}.json"
        out_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        print(f"  Wrote {out_path.relative_to(Path(__file__).parent.parent)}")


def main() -> None:
    print("Generating external-runner JSON Schema files...")
    schemas: dict[str, dict] = generate_schemas()
    write_schemas(schemas)
    print(f"Done — {len(schemas)} schema file(s) written to {OUTPUT_DIR.relative_to(Path(__file__).parent.parent)}/")


if __name__ == "__main__":
    main()
