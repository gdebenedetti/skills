#!/usr/bin/env python3
"""Minimal validation for Agent Skill directories."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

MAX_SKILL_NAME_LENGTH = 64
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}


def validate_skill(skill_path: str) -> tuple[bool, str]:
    skill_dir = Path(skill_path)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    content = skill_md.read_text()
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return False, f"Invalid YAML in frontmatter: {exc}"

    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a YAML dictionary"

    unexpected_keys = set(frontmatter.keys()) - ALLOWED_FRONTMATTER_KEYS
    if unexpected_keys:
        allowed = ", ".join(sorted(ALLOWED_FRONTMATTER_KEYS))
        unexpected = ", ".join(sorted(unexpected_keys))
        return False, f"Unexpected key(s): {unexpected}. Allowed: {allowed}"

    for key in ("name", "description"):
        if key not in frontmatter:
            return False, f"Missing '{key}' in frontmatter"

    name = frontmatter["name"]
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, f"Name '{name}' must use lowercase hyphen-case"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
    if len(name) > MAX_SKILL_NAME_LENGTH:
        return False, f"Name is too long ({len(name)} > {MAX_SKILL_NAME_LENGTH})"

    description = frontmatter["description"]
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets"
    if len(description) > 1024:
        return False, f"Description is too long ({len(description)} > 1024)"

    return True, "Skill is valid!"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/quick_validate.py <skill_directory>")
        return 1

    valid, message = validate_skill(argv[1])
    print(message)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
