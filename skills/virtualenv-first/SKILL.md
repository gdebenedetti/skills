---
name: virtualenv-first
description: Use when running Python commands or installing Python dependencies. Prefer the project's virtual environment and avoid global or system-level Python when an isolated environment is available.
---

# Virtualenv First

Use this skill for Python setup, installs, tests, linters, and app commands.

- Prefer the project's virtual environment (`.venv`, `venv`, or the repo-documented env) for `python`, `pip`, `pytest`, and CLI entrypoints.
- Activate it or call binaries directly, for example `.venv/bin/python` or `.venv/bin/pytest`.
- Avoid global installs and global Python unless the task explicitly requires system scope or no project environment exists.
- If no environment exists, create one before installing Python dependencies.
- When documenting commands, show the virtualenv-aware form first.
