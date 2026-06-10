#!/usr/bin/env python3
"""KnowledgeVault — local-first automatic knowledge management."""

import sys

from knowledgevault.app import run


def main() -> int:
    seed = "--seed" in sys.argv or "-s" in sys.argv
    return run(seed_example_data=seed)


if __name__ == "__main__":
    sys.exit(main())
