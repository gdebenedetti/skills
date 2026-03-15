# Contributing

## Skill Format

- Put each skill in `skills/<skill-name>/`.
- Use lowercase hyphen-case names.
- `SKILL.md` is required.
- `agents/` is optional and non-canonical.
- Add `scripts/`, `references/`, or `assets/` only when they are necessary.

## Quality Gates

Every new or changed skill must pass both gates before merge.

### 1. Automated validation

Run:

```bash
python scripts/validate_skills.py
```

### 2. Anthropic `skill-creator` review

Use Anthropic `skill-creator` as the official review guide for authoring quality.

This is not a separate validator skill. It is a skill-creation and improvement workflow that includes `quick_validate.py` plus authoring guidance.

Review the skill against that guidance and confirm all of the following:

- The skill name is short, clear, and correctly hyphen-cased.
- The frontmatter `name` and `description` are good triggers for invocation.
- `SKILL.md` is concise, procedural, and focused on the workflow.
- Detailed material lives in `references/` instead of bloating `SKILL.md`.
- `scripts/` and `assets/` are present only when they add real reusable value.
- Agent-specific metadata is optional and consistent with `SKILL.md` when present.
- The skill does not duplicate unnecessary context or repo process documentation.

## Pull Requests

- Keep each PR scoped to one coherent change.
- Include validation results in the PR description.
- Do not merge a skill change without explicit human confirmation that the `skill-creator` checklist was reviewed.
