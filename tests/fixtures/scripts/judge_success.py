"""Fixture script for external judge: reads request.json, writes a valid judge response.json.

Returns score=0.8, reasoning="looks good", plus echoes back the inbound trace_id.
"""

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
            "score": 0.8,
            "reasoning": "The output looks good based on the criteria.",
        },
        "metadata": {"total_latency_ms": 10},
        "trace_id": trace_id,
    }

    Path("response.json").write_text(json.dumps(response), encoding="utf-8")
    sys.exit(0)


if __name__ == "__main__":
    main()
