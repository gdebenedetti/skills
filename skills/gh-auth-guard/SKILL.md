---
name: gh-auth-guard
description: Verify and rehydrate GitHub CLI authentication in this local Codex environment before running `gh` commands. Use when a task depends on `gh`, when a new chat session may not have inherited `GH_TOKEN`, when `gh auth status` disagrees with `gh api`, or when GitHub network failures in a sandboxed session could be confused with invalid credentials.
---

# GH Auth Guard

Run a preflight before any workflow that depends on `gh`.

## Workflow

1. Run `$HOME/.codex/skills/private/gh-auth-guard/scripts/ensure-gh-auth.sh`.
2. Treat `gh api user --jq .login` as the primary auth check when network is available.
3. Do not use `gh auth status` as the primary check inside a sandboxed Codex session.

Set `GH_AUTH_PROFILE=classic` before the guard when a workflow needs GitHub APIs that fine-grained PATs cannot access, such as repository check-runs.

## Outcomes

- `ok: LOGIN`
  Continue with the requested `gh` workflow.
- `ok: LOGIN (rehydrated from .../codex-token.env)`
  The session was missing `GH_TOKEN`; the script repaired it by sourcing `$HOME/.config/gh/codex-token.env`.
- `missing_profile_token: ...`
  `GH_AUTH_PROFILE` was set, but the matching token variable was not present in the session or persisted env file.
- `missing_token: ...`
  There is no token in the session and no persisted token file. Run `gh auth login -h github.com --git-protocol https --web`, then refresh `$HOME/.config/gh/codex-token.env`.
- `token_invalid: ...`
  A token was loaded, but GitHub rejected it. Re-authenticate and refresh `$HOME/.config/gh/codex-token.env`.
- `network_unavailable: ...`
  This is a network reachability problem for the current session, not an auth failure. Retry outside the sandbox or with network access.
- `auth_check_failed: ...`
  The `gh api` check failed in a way the script did not classify. Inspect stderr and retry with network access.

## Rules

- Prefer `gh api user --jq .login` over `gh auth status` for the primary health check.
- Never print tokens.
- Treat `$HOME/.config/gh/codex-token.env` as the canonical local source for `GH_TOKEN`.
- Load `$HOME/.config/gh/codex-token.env` before declaring the session unauthenticated.
- Use `GH_AUTH_PROFILE` to select a persisted token profile:
  - `default` or unset: use the current effective `GH_TOKEN`.
  - `classic`: export `GH_TOKEN_CLASSIC` as the effective `GH_TOKEN`.
  - `finegrained` or `fg`: export `GH_TOKEN_FINEGRAINED` as the effective `GH_TOKEN`.
- Use `GH_AUTH_PROFILE=classic` for flows that read GitHub check-runs. Fine-grained PATs do not expose the Checks API permissions needed for those endpoints.
- If `git push https://github.com/...` fails with `Could not resolve host: github.com` while `curl https://github.com` or direct top-level `gh api` works, treat that as a sandbox or session network limitation, not as bad GitHub credentials.

## Repair Flow

If the script reports `missing_token` or `token_invalid`, use:

```bash
gh auth login -h github.com --git-protocol https --web
TOKEN="$(gh auth token)"
umask 077
printf "export GH_TOKEN='%s'\nexport GITHUB_TOKEN=\"\$GH_TOKEN\"\n" "$TOKEN" > "$HOME/.config/gh/codex-token.env"
chmod 600 "$HOME/.config/gh/codex-token.env"
```

Ensure `$HOME/.zshenv` sources the persisted token:

```bash
[ -r "$HOME/.config/gh/codex-token.env" ] && . "$HOME/.config/gh/codex-token.env"
```

For multiple token profiles, persist explicit variables and choose the effective token:

```bash
export GH_TOKEN_FINEGRAINED='...'
export GH_TOKEN_CLASSIC='...'

export GH_TOKEN="$GH_TOKEN_CLASSIC"
export GITHUB_TOKEN="$GH_TOKEN"
```

Then run a profile-specific check when needed:

```bash
GH_AUTH_PROFILE=classic $HOME/.codex/skills/private/gh-auth-guard/scripts/ensure-gh-auth.sh
```

## Validation

Run the unit-style mock tests with:

```bash
$HOME/.codex/skills/private/gh-auth-guard/scripts/test-ensure-gh-auth.sh
```
