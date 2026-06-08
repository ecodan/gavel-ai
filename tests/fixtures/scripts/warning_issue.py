"""Fixture script: writes status=ok with an issue of level=warning, exits 0."""

import json
import sys
from pathlib import Path


def main() -> None:
    response = {
        "status": "ok",
        "result": {},
        "issue": {
            "code": "low_confidence",
            "level": "warning",
            "message": "test",
        },
    }
    Path("response.json").write_text(json.dumps(response), encoding="utf-8")
    sys.exit(0)


if __name__ == "__main__":
    main()
