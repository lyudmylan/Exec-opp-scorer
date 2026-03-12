# Executive Opportunity Scorer

Executive Opportunity Scorer is a traceable research tool for evaluating whether an Israeli SaaS startup is likely to need a VP R&D or equivalent within the next 12 months.

The v1 product is intentionally narrow:
- Public-web signals only
- One company at a time
- Explainable weighted heuristics instead of ML
- Output optimized for a VP R&D candidate deciding whether to pursue outreach

## What It Produces
- `fit score`: likelihood the company will need a VP R&D soon
- `risk score`: likelihood the opportunity is unstable, weak, or misleading
- `confidence`: evidence quality and coverage
- `recommendation`: `Pursue now`, `Monitor`, or `Low priority`
- `explanation`: concise rationale grounded in evidence
- `next steps`: recommended actions for the candidate

## Repository Layout
- `docs/scoring_rubric.md`: scoring philosophy, signal catalog, weights, and thresholds
- `docs/best_practices.md`: implementation and operating guidelines
- `docs/code_review.md`: reviewer checklist for scoring and traceability changes
- `.github/workflows/ci.yml`: GitHub Actions test pipeline
- `executive_opportunity_scorer/`: scoring engine and CLI
- `data/samples/`: sample company inputs for calibration and demos
- `tests/`: acceptance and unit tests

## Usage
Run against a sample file:

```bash
python3 -m executive_opportunity_scorer.cli score data/samples/series_b_growth.json
```

Print JSON output:

```bash
python3 -m executive_opportunity_scorer.cli score data/samples/series_b_growth.json --format json
```

List sample scenarios:

```bash
python3 -m executive_opportunity_scorer.cli list-samples
```

## Testing

```bash
python3 -m unittest discover -s tests -v
```

## CI
GitHub Actions runs the test suite on every push and pull request using `.github/workflows/ci.yml`.
