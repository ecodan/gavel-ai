"""Fixture script for external judge: returns score with a warning-level issue."""

import json
import sys
from pathlib import Path


def main() -> None:
    request_path = Path("request.json")
    if request_path.exists():
        request_data = json.loads(request_path.read_text(encoding="utf-8"))
    else:
        request_data = {}

    trace_id = request_data.get("trace_id")

    response = {
        "status": "ok",
        "result": {
            "score": 5,
            "reasoning": "Partial match with some concerns.",
        },
        "issue": {
            "code": "low_confidence",
            "level": "warning",
            "message": "Judge confidence below threshold",
        },
        "metadata": {},
        "trace_id": trace_id,
    }

    Path("response.json").write_text(json.dumps(response), encoding="utf-8")
    sys.exit(0)


if __name__ == "__main__":
    main()
