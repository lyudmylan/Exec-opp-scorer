# Best Practices

## Product
- Keep the scope narrow: Israeli SaaS startups, VP R&D candidate persona, 12-month prediction target.
- Keep `fit`, `risk`, and `confidence` separate throughout data modeling, scoring, and UX.
- Prefer evidence-backed scorecards over free-form summaries.
- Optimize for decision support, not automation of judgment.

## Data
- Store every evidence item with URL, publication date if known, access timestamp, and a short note.
- Treat missing evidence as uncertainty, not as a negative signal.
- Prefer explicit freshness windows per signal over one global staleness rule.
- Preserve raw observations alongside normalized values for auditability.
- Flag excluded or gray-area sectors early and stop scoring if the company is out of scope.

## Modeling
- Start with explicit heuristics and keep feature semantics stable.
- Track fired signals and weight contributions for each result.
- Separate “need likelihood” from “opportunity risk” to avoid hiding tradeoffs.
- Make confidence an explicit score so sparse public data does not produce false precision.

## Evaluation
- Maintain a benchmark set with positive, negative, and borderline examples.
- Review false positives and false negatives manually before changing weights.
- Calibrate thresholds for actionability, not for maximizing one abstract metric.
- Version the rubric when weights or thresholds change.

## Delivery
- Build one-company workflows before batch ranking.
- Show source evidence in the output so a user can verify claims quickly.
- Capture reviewer feedback for later calibration, even if it is stored manually at first.
- Keep the CLI and output schema stable so a UI can be added later without rewriting the core engine.
