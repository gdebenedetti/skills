---
name: prepare-plan-implementation
description: Review and structure implementation plans before execution. Use when Codex is in Plan mode, drafting or revising an implementation plan, deciding whether to offer implementation next, or translating a plan into execution. Require an explicit assessment of whether the work should stay in the current branch, move to a new branch, or use a separate worktree, then organize the implementation into bounded incremental stages with clear scope limits, progress checks, verification, and tests.
---

# Prepare Plan Implementation

Use this skill before moving from planning to implementation.

## Gate The Plan

- Inspect repository context first when possible with non-destructive commands such as `git status --short --branch`.
- State one explicit isolation recommendation before offering implementation: `current branch`, `new branch`, or `new worktree`.
- Justify the recommendation briefly using the expected blast radius, change duration, need for parallel work, current workspace cleanliness, and risk of exploratory refactors.
- If isolation is not needed, say so explicitly. Do not skip the assessment.
- Prefer the lightest viable option.
- Recommend `current branch` for a small, low-risk change that clearly belongs to the active stream of work.
- Recommend `new branch` for a coherent change that should be reviewed, tested, and landed separately.
- Recommend `new worktree` for long-running, risky, or parallel work that should not disturb the current checkout.
- Reassess the recommendation if the scope expands materially.
- If repository context is unknown, state the assumptions behind the recommendation.
- If the working tree is already dirty, avoid suggestions that silently mix unrelated changes or assume cleanup authority.

## Escalate To Worktree

- Treat `new worktree` as the safer default when physical checkout isolation matters, not just git history isolation.
- Recommend `new worktree` immediately if the current working tree is dirty with unrelated changes and implementation should proceed without touching them.
- Recommend `new worktree` immediately if the plan is expected to span multiple sessions, significant exploratory work, or frequent context switching with the current task.
- Recommend `new worktree` immediately if the work is likely to require disruptive operations in the checkout such as dependency churn, code generation, long-lived dev processes, or broad refactors.
- Recommend `new worktree` immediately if the user will likely need the current checkout to stay stable for review, hotfixes, or parallel implementation.
- Do not recommend `new branch` as sufficient when the real need is checkout isolation. A branch in the same worktree still shares uncommitted files.
- If two or more moderate risk signals are present, prefer `new worktree` unless there is a clear reason not to.
- Moderate risk signals include more than three planned stages, likely rebases or back-and-forth experimentation, touching many directories, or unclear rollback boundaries.
- If recommending `current branch` or `new branch`, say why shared checkout state is safe enough.

## Stage The Implementation

- Break the plan into incremental stages.
- Give every stage a goal, scope, explicit boundary, verification method, tests or checks, and exit criteria.
- Keep each stage small enough to complete and validate independently.
- Separate enabling refactors from behavior changes unless they are inseparable.
- Keep unrelated cleanup out of the current stage.
- Prefer stages that can be verified before moving to the next one.

## Verify Progress

- Define at least one concrete verification step per stage.
- Name exact commands when repository context makes them knowable.
- If automated coverage is absent, specify the manual verification path and call out the gap.
- Confirm stage completion against the exit criteria before proposing the next stage.
- Treat test and verification work as part of the stage, not as an optional follow-up.

## Offer Implementation Carefully

- If the user asked only for a plan, stop after the staged plan.
- If implementation is in scope, offer it only after the isolation recommendation and staged outline are present.
- Describe implementation as stage-by-stage execution, not as one undifferentiated change.
- Keep the first stage narrow enough to reduce rollback cost if assumptions break.

## Use This Response Shape

- `Isolation:` recommend `current branch`, `new branch`, or `new worktree`.
- `Reason:` explain why that level of isolation is or is not necessary.
- `Stage 1:` name the first bounded step.
- `Limit:` state what the stage must not include.
- `Verification:` state how completion will be checked.
- `Tests:` name the concrete automated or manual checks.
- Repeat the same shape for later stages when needed.
