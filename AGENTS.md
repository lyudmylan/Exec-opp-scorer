# AGENTS.md

This file defines the default operating contract for coding agents working in this repository.

## Purpose
- Keep changes safe, reviewable, and easy to ship.
- Optimize for correctness in scoring behavior, evidence handling, and output quality.
- Minimize coordination overhead by using one owner agent on the critical path.

## Default Workflow
1. Implement the requested change locally.
2. Run the full local test suite:
   `python3 -m unittest discover -s tests -v`
3. Run one independent review pass focused on bugs, regressions, and missing tests.
4. Fix anything found.
5. Re-run the full local test suite.
6. Commit with a clear, scoped message.
7. Push the branch.
8. Check remote CI before marking the work complete.

See also: [docs/shipping_workflow.md](docs/shipping_workflow.md)

## Delegation Rules
- Keep implementation ownership, test execution, fixes, commit, push, and CI checks in the main agent thread.
- Use at most one review sub-agent by default.
- Only use multiple sub-agents when the workstreams are clearly separated and write scopes do not overlap.
- Do not split routine sequential tasks like test, commit, push, and CI into separate sub-agents.

## Review Priorities
Review in this order:
1. Scoring or recommendation behavior changes
2. Evidence traceability and explanation consistency
3. Missing-data and scope-handling behavior
4. Test coverage for changed behavior
5. UI regressions in core score and pipeline flows

See also: [docs/code_review.md](docs/code_review.md)

## Testing Standard
- Always run `python3 -m unittest discover -s tests -v` before commit.
- Any scoring logic change should include or update tests.
- Any schema or output-field change should update tests and docs.
- If a change affects browser behavior but there is no browser test framework, document the residual risk explicitly in the final handoff.

## Git Rules
- Prefer feature branches and PRs when practical.
- Never rewrite or discard user changes unless explicitly requested.
- Never use destructive git commands like `git reset --hard` unless explicitly requested.
- Keep commit messages scoped to the behavior being changed.

## Completion Standard
Do not mark work complete if:
- local tests are failing
- review findings are unresolved
- docs or tests are stale relative to the code
- remote CI has not been checked after push

## Optional Branch Protection
Recommended defaults for agent-friendly work:

### Lightweight
- Protect `main` with required status checks
- Allow admins to bypass when necessary
- Do not require PRs

This works well for solo or fast-moving agent-driven development where direct pushes are still acceptable but CI should stay green.

### Strict
- Protect `main` with required status checks
- Require pull requests before merge
- Optionally require conversation resolution
- Allow admin bypass only for emergencies

This works better for team workflows or higher-risk repos.

For setup guidance, see: [docs/branch_protection.md](docs/branch_protection.md)
