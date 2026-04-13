# Copyright 2026 Cicadas Contributors
# SPDX-License-Identifier: Apache-2.0

import json
from datetime import UTC, datetime
from pathlib import Path

VALID_SOURCES = {"agent-reported", "unavailable", "estimated"}


def init_log(log_path: Path) -> None:
    """Create tokens.json with empty entries list if it doesn't exist."""
    log_path = Path(log_path)
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w") as f:
            json.dump({"entries": []}, f, indent=2)


def load_log(log_path: Path) -> list[dict]:
    """Return entries list. Returns [] if file absent or corrupt, never raises."""
    try:
        log_path = Path(log_path)
        if not log_path.exists():
            return []
        with open(log_path) as f:
            data = json.load(f)
        return data.get("entries", [])
    except (json.JSONDecodeError, OSError):
        return []


def append_entry(
    log_path: Path,
    initiative: str,
    phase: str,
    source: str,
    *,
    subphase: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached_tokens: int | None = None,
    model: str | None = None,
    notes: str | None = None,
) -> None:
    """Append a validated token entry to the log. Creates file if absent."""
    if not initiative:
        raise ValueError("initiative is required")
    if not phase:
        raise ValueError("phase is required")
    if source not in VALID_SOURCES:
        raise ValueError(f"source must be one of {VALID_SOURCES}, got {source!r}")

    entry: dict = {
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "initiative": initiative,
        "phase": phase,
        "subphase": subphase,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_tokens": cached_tokens,
        "model": model,
        "source": source,
        "notes": notes,
    }

    log_path = Path(log_path)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entries = load_log(log_path)
        entries.append(entry)
        with open(log_path, "w") as f:
            json.dump({"entries": entries}, f, indent=2)
    except OSError as e:
        print(f"[WARN] Could not write token entry to {log_path}: {e}")
