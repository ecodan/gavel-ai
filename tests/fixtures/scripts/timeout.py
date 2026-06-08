"""Fixture script: sleeps forever to simulate a timeout."""

import time


def main() -> None:
    time.sleep(999)


if __name__ == "__main__":
    main()
