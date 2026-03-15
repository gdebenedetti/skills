# Agent Skills

Generic catalog of reusable Agent Skills.

## What Is Here

Each skill lives in `skills/<skill-name>/` and is centered on `SKILL.md`.

`SKILL.md` is the portable contract. Files under `agents/` are optional adapters for specific runtimes.

Current skills:

- `commit-practices`
- `mcp-builder`
- `prepare-plan-implementation`
- `virtualenv-first`

## Layout

```text
skills/
  <skill-name>/
    SKILL.md
    agents/
    scripts/
    references/
    assets/
scripts/
  quick_validate.py
  validate_skills.py
```

Only `SKILL.md` is required. The other folders are optional.

## Use With skills.sh

Use this repository directly with `skills.sh`:

```bash
npx skills add . --list
```

Install one specific skill:

```bash
npx skills add . --skill commit-practices
npx skills add . --skill mcp-builder
npx skills add . --skill prepare-plan-implementation
npx skills add . --skill virtualenv-first
```

Install the whole catalog:

```bash
npx skills add . --skill '*' --yes
```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

Every new or changed skill must pass both checks:

1. `python scripts/validate_skills.py`
2. Editorial review guided by Anthropic `skill-creator`

## Licensing

Unless a skill includes its own license file, repository content is available under the MIT license in [LICENSE](./LICENSE).

Some bundled skills may preserve their original license where required. For example, `skills/mcp-builder/` includes its own `LICENSE.txt`.

## Publishing Checklist

- Keep the repository description neutral and agent-agnostic.
- Use generic GitHub topics such as `agent-skills`, `ai-agents`, `prompt-engineering`, and `developer-tools`.
- Confirm the GitHub Community Profile is complete before making the repository public.
