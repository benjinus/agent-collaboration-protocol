#!/usr/bin/env python3
import argparse
from pathlib import Path

from _acp import validate_folder


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an Agent Collaboration Protocol folder.")
    parser.add_argument("--folder", required=True, help="Collaboration folder")
    args = parser.parse_args()
    errors, warnings = validate_folder(Path(args.folder).expanduser().resolve())

    if errors:
        print("ACP validation failed")
        for item in errors:
            print(f"ERROR: {item}")
        for item in warnings:
            print(f"WARNING: {item}")
        return 2
    if warnings:
        print("ACP validation passed with warnings")
        for item in warnings:
            print(f"WARNING: {item}")
        return 1
    print("ACP validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

