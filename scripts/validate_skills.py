#!/usr/bin/env python3
"""Validate every skill in the repository."""

from __future__ import annotations

import sys
from pathlib import Path

from quick_validate import validate_skill


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    skills_root = repo_root / "skills"
    skill_dirs = sorted(path for path in skills_root.iterdir() if path.is_dir())

    if not skill_dirs:
        print("No skill directories found.")
        return 1

    failures = 0
    for skill_dir in skill_dirs:
        valid, message = validate_skill(str(skill_dir))
        print(f"{skill_dir.name}: {message}")
        if not valid:
            failures += 1

    if failures:
        print(f"\nValidation failed for {failures} skill(s).")
        return 1

    print(f"\nValidated {len(skill_dirs)} skill(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
