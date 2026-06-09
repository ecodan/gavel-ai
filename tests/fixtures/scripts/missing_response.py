"""Fixture script: exits 0 but does NOT write response.json."""

import sys


def main() -> None:
    # Intentionally write nothing — no response.json
    sys.exit(0)


if __name__ == "__main__":
    main()
