# Shipping Workflow

Use this sequence for routine code changes unless the task explicitly calls for a different process.

## Default Sequence
1. Implement the requested change locally.
2. Run the full local test suite:
   `python3 -m unittest discover -s tests -v`
3. Do an independent code review pass focused on bugs, regressions, and missing tests.
4. Fix anything found in testing or review.
5. Re-run the full local test suite.
6. Commit the changes with a clear, scoped message.
7. Push the branch to GitHub.
8. Check remote CI and confirm it passes before considering the work done.

## Delegation Guidance
- Keep test execution, fixes, commit, push, and CI checks in the main thread.
- If parallel help is useful, use one sub-agent for an independent review pass.
- Do not split each step into a separate sub-agent unless the work is unusually large or the write scopes are cleanly separated.

## Merge Standard
Do not push as complete if:
- local tests are failing
- review findings are unresolved
- the output schema changed without updating tests or docs
- CI has not been checked after push
