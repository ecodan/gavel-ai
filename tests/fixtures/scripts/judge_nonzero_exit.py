"""Fixture script for external judge: exits with code 1 (PROCESS_FAILURE)."""

import sys


def main() -> None:
    sys.exit(1)


if __name__ == "__main__":
    main()
