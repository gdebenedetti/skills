---
name: sync-main-after-merge
description: Use when a branch or worktree has been merged into `main` or `master`, or when Codex is asked to do that merge and then resynchronize the local default branch with the remote. Keep the default branch clean, current, and aligned with origin.
---

# Sync Main After Merge

Use this skill for merge-completion tasks on the default branch.

1. Identify the repo's default branch.
   - Prefer `origin/HEAD` when it exists.
   - Fall back to `main`, then `master`.
2. Check the target checkout for a clean worktree.
   - If uncommitted or untracked changes exist, stop before overwriting anything.
3. Fetch and prune remote refs.
   - `git fetch origin --prune`
4. If the request includes the merge itself, merge the topic branch or worktree branch into the default branch first.
   - Use the branch the user named, or the branch currently associated with the worktree.
   - Prefer fast-forward or the repo's documented merge policy.
5. Switch to the default branch locally.
   - `git switch <default-branch>`
6. Sync the local default branch with remote.
   - Use `git pull --ff-only` for the normal case.
   - If the user explicitly wants the local branch to match `origin/<default-branch>` exactly and the worktree is clean, use `git reset --hard origin/<default-branch>` after fetching.
7. Verify the result.
   - `git status --short --branch`
   - Confirm the local branch and `origin/<default-branch>` point to the expected commit.

## Guardrails

- Use `git switch`, not `git checkout`.
- Never discard local changes unless the user explicitly asked for an exact remote match.
- Do not assume `main`; use `master` only when that is the actual default branch.
- If the target branch is ambiguous, resolve that before changing history.
