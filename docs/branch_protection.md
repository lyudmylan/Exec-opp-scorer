# Branch Protection

This repo can support two practical branch-protection modes.

## Recommended Choice
For agent-friendly solo development, start with **Lightweight** protection:
- keep `main` protected by CI
- allow direct pushes when needed
- avoid blocking work on mandatory PR creation

If the repo becomes more collaborative or higher risk, move to **Strict** protection.

## Lightweight Protection
Use when:
- one person or one main agent owns most changes
- speed matters more than process overhead
- CI should still protect `main`

Suggested settings:
- branch: `main`
- required status checks: `test`
- require branches to be up to date before merging: `true`
- require pull request reviews: `false`
- require pull request before merge: `false`
- allow admin bypass: `true`

## Strict Protection
Use when:
- multiple people or multiple agents contribute regularly
- you want all changes reviewed through PRs
- you want GitHub to block direct pushes to `main`

Suggested settings:
- branch: `main`
- required status checks: `test`
- require branches to be up to date before merging: `true`
- require pull request before merge: `true`
- require approving reviews: `true`
- require conversation resolution: `true`
- allow admin bypass: `true` or `false` depending on your tolerance for emergency overrides

## Applying Protection
The safest path is to set this in the GitHub web UI:
1. Open the repository on GitHub.
2. Go to `Settings` -> `Branches`.
3. Edit the rules for `main`.
4. Apply either the Lightweight or Strict profile above.

## Notes For Agents
- If PRs are required, the default shipping flow becomes:
  create branch -> commit -> push branch -> open PR -> wait for CI -> merge
- If PRs are not required, the default flow remains:
  commit -> push -> check CI
- Even with lightweight protection, agents should still prefer green CI before considering work complete.
