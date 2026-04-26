#!/usr/bin/env python3
"""Helper for mutation testing the FastAPI backend.

Same surface as the iOS scripts/mutate.py (check / apply / revert / revert-all)
so the mutation_test.sh runner shape stays consistent across stacks.
"""
import os
import sys
from pathlib import Path


def _backup_path(filepath: str, token: str | None) -> str:
    return f"{filepath}.mut.bak.{token}" if token else f"{filepath}.mut.bak"


def main():
    action = sys.argv[1]

    if action == "check":
        filepath, search = sys.argv[2], sys.argv[3]
        with open(filepath) as f:
            content = f.read()
        sys.exit(0 if search in content else 1)

    if action == "apply":
        filepath, search, replace = sys.argv[2], sys.argv[3], sys.argv[4]
        token = sys.argv[5] if len(sys.argv) > 5 else None
        with open(filepath) as f:
            content = f.read()
        bak = _backup_path(filepath, token)
        if not os.path.exists(bak):
            with open(bak, "w") as f:
                f.write(content)
        if search not in content:
            sys.exit(2)
        with open(filepath, "w") as f:
            f.write(content.replace(search, replace, 1))
        return

    if action == "revert":
        filepath = sys.argv[2]
        token = sys.argv[3] if len(sys.argv) > 3 else None
        bak = _backup_path(filepath, token)
        if os.path.exists(bak):
            with open(bak) as f:
                original = f.read()
            with open(filepath, "w") as f:
                f.write(original)
            os.remove(bak)
        return

    if action == "revert-all":
        for bak in Path(".").rglob("*.mut.bak*"):
            original_path = str(bak).split(".mut.bak")[0]
            if os.path.exists(original_path):
                with open(bak) as f:
                    original = f.read()
                with open(original_path, "w") as f:
                    f.write(original)
            os.remove(bak)
        return

    print(f"Unknown action: {action}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
