"""Fixture script: reads request.json, writes a valid response.json, exits 0."""

import json
import sys
from pathlib import Path


def main() -> None:
    request_path = Path("request.json")
    if request_path.exists():
        request_data = json.loads(request_path.read_text(encoding="utf-8"))
    else:
        request_data = {}

    response = {
        "status": "ok",
        "result": {"output": "test_output"},
        "metadata": {},
        "trace_id": request_data.get("trace_id"),
    }

    Path("response.json").write_text(json.dumps(response), encoding="utf-8")
    sys.exit(0)


if __name__ == "__main__":
    main()
