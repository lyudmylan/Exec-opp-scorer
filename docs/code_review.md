# Code Review Guide

This project is a decision-support system, so review should optimize for correctness, traceability, and safe evolution of the scoring rubric before it optimizes for style.

## Review Priorities
Review in this order:
1. Scoring behavior and recommendation changes
2. Evidence traceability and explanation quality
3. Scope enforcement and missing-data handling
4. Test coverage for changed behavior
5. Code clarity and maintainability

## What Reviewers Should Look For

### 1. Behavioral correctness
- Does the change alter `fit`, `risk`, `confidence`, or recommendation thresholds?
- Does it change how blockers are handled?
- Could it make a company look more attractive or lower-risk without strong evidence?
- Could it silently break out-of-scope filtering?

### 2. Traceability
- Is every meaningful scoring outcome still grounded in explicit evidence or structured input?
- If a rule changes, is the explanation still consistent with the score?
- Are source references preserved in the result output?

### 3. Missing and conflicting data
- Is missing data treated as uncertainty rather than negative evidence?
- Does stale evidence reduce confidence instead of being treated as fresh?
- Do conflicting public signals surface as lower confidence or ambiguity in the explanation?

### 4. Test expectations
- Any change to scoring logic should update or add a scenario test.
- Any change to scope rules should add a scope test.
- Any change to CLI or output schema should preserve core fields or document the breaking change.

## Review Comment Format
Each finding should include:
- severity: `high`, `medium`, or `low`
- location: file and function
- issue: what is wrong
- impact: why it matters to the user or the score
- fix direction: the smallest safe correction

Example:

```text
Severity: high
Location: executive_opportunity_scorer/engine.py::_recommend
Issue: A strong blocker can still result in `Pursue now`.
Impact: Users may be pushed toward companies that already have a mature R&D leader.
Fix direction: Gate `Pursue now` when blocker pressure exceeds the calibrated threshold.
```

## Merge Standard
Do not merge if:
- recommendation behavior changed without tests
- rubric semantics changed without doc updates
- explanation text can contradict the computed score
- confidence logic masks sparse or stale data
- the full test suite is not green
