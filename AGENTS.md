# AGENTS.md instructions for /Users/guidodebenedetti/github/skills

- This repo is a generic catalog of Agent Skills.
- Keep skills in `skills/<skill-name>/`.
- `SKILL.md` is the canonical interface.
- Agent-specific files under `agents/` are optional adapters.
- Use lowercase hyphen-case names.
- Keep instructions short, direct, and procedural.
- Reuse `scripts/`, `references/`, and `assets/` only when they add real value.
- Expose local skills with symlinks instead of copies.
- Run `python scripts/validate_skills.py` after edits.
- Review every new or changed skill against Anthropic `skill-creator`, not only `quick_validate.py`.
