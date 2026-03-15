---
name: commit-practices
description: Use when planning, reviewing, or writing git commits. Keep commits atomic and small, use English commit messages, describe concrete functionality, and follow Conventional Commits.
---

# Commit Practices

Use this skill when preparing a commit or deciding whether a change should be split.

- One commit, one coherent change that can be reviewed and tested on its own.
- Split unrelated fixes, refactors, docs, and tests unless the test or doc change belongs directly to the same behavior change.
- Keep commits small. If the subject needs "and", it is probably two commits.
- Write commit messages in English.
- Use the Conventional Commits format: `<type>[optional scope]: <description>`.
- Prefer clear types such as `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`, `perf`, `style`, and `revert`.
- Write the description as a concise statement of concrete functionality or behavior. Prefer `feat(auth): add session timeout warning` over `wip`, `more updates`, `address feedback`, or `continue work`.
- Use an optional body when the why or the impact is not obvious from the subject alone.
- Mark breaking changes explicitly with `!` after the type or scope, and describe them in a `BREAKING CHANGE:` footer when relevant.
- Before committing, check `git diff --staged` and confirm the staged change matches a single sentence and the chosen type still fits that sentence.
