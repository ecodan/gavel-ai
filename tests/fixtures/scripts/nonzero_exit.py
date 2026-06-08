"""Fixture script: exits with code 1 and writes a message to stderr."""

import sys


def main() -> None:
    sys.stderr.write("nonzero_exit fixture: simulated failure\n")
    sys.stderr.flush()
    sys.exit(1)


if __name__ == "__main__":
    main()
