# Executive Opportunity Scorer

A decision-support tool for a VP R&D candidate evaluating Israeli SaaS startups as proactive outreach targets — even before a vacancy is posted.

Enter a few quick-triage facts about a company and get a scored, explainable verdict: whether to pursue outreach now, monitor, or skip.

## What It Produces

| Field | Description |
|---|---|
| `fit_score` | 0–100 likelihood the company needs a VP R&D soon |
| `risk_score` | 0–100 opportunity risk (layoffs, freeze, instability) |
| `confidence` | 0–100 evidence quality and coverage |
| `recommendation` | `Pursue now`, `Monitor`, or `Low priority` |
| `timing_window` | `Optimal`, `Good`, `Early`, `Late`, `Blocked`, or `Unclear` |
| `approach_angle` | Actionable pitch angle and who to contact, derived from signals |
| `explanation` | Concise rationale grounded in fired signals |
| `next_steps` | Recommended actions for the candidate |

## Key Features

- **Schema-driven UI** — browser form rendered from `data/ui_spec/company_form.json`; only ~5 fields to fill manually
- **Approach angle** — tells you what to pitch and who to contact based on the strongest signals (non-technical founder → CEO directly; leadership gap → scaling inflection pitch; senior churn → stability framing)
- **Timing window** — derived from funding recency + hiring momentum; tells you whether now is the right moment to reach out
- **Pipeline** — save scored companies, track them over time, delete when done; persisted to `pipeline.db` (SQLite)
- **LLM enrichment** — "Enrich from URL" button calls Claude to pre-fill company stage, team size, and engineering leadership from a company URL (requires `ANTHROPIC_API_KEY`)
- **Explainable heuristics** — weighted signals, not ML; every score is traceable to evidence

## Design Principles

- Public-web signals only
- One company at a time (pipeline view for tracking multiple)
- Explainable weighted heuristics instead of ML
- Separate fit / risk / confidence scores
- Evidence attached to every signal with source URL and date

## Repository Layout

```
executive_opportunity_scorer/   scoring engine, CLI, web server, storage, enricher
data/ui_spec/                   company_form.json — schema-driven form definition
data/samples/                   sample company inputs for calibration and demos
docs/                           scoring rubric, best practices, code review guide
tests/                          56 tests covering engine, webapp, storage, enricher
.github/workflows/ci.yml        GitHub Actions CI pipeline
```

## Running the UI

```bash
python3 -m executive_opportunity_scorer.cli serve-ui
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Optional flags:
```bash
python3 -m executive_opportunity_scorer.cli serve-ui --port 9000      # different port
python3 -m executive_opportunity_scorer.cli serve-ui --host 0.0.0.0   # expose on network
```

To enable LLM enrichment, set your Anthropic API key before starting:
```bash
ANTHROPIC_API_KEY=sk-ant-... python3 -m executive_opportunity_scorer.cli serve-ui
```

## CLI Usage

Score a company from a JSON file:
```bash
python3 -m executive_opportunity_scorer.cli score data/samples/series_b_growth.json
python3 -m executive_opportunity_scorer.cli score data/samples/series_b_growth.json --format json
```

List bundled sample scenarios:
```bash
python3 -m executive_opportunity_scorer.cli list-samples
```

## Testing

```bash
python3 -m unittest discover -s tests -v
```

56 tests covering: scoring engine scenarios, timing window states, approach angle branches, storage CRUD, enricher response parsing, and webapp form coercion.

## CI

GitHub Actions runs the full test suite on every push and pull request via `.github/workflows/ci.yml`.
