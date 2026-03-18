# Scoring Rubric

## Prediction Target
The system estimates whether an Israeli SaaS startup is likely to need a VP R&D or equivalent within the next 12 months.

Equivalent titles:
- VP R&D
- VP Engineering
- Head of R&D
- Engineering executive directly owning the full R&D organization

## Scope Rules
Included:
- Israeli SaaS startups

Excluded:
- Gambling
- Gaming
- Forex
- Pure hardware
- Adtech
- Any company explicitly flagged as gray-area by the reviewer

## Score Semantics
- `fit score`: emerging demand for a VP R&D-type hire
- `risk score`: reasons the opportunity may be unattractive or timing may be poor
- `confidence`: source coverage, source agreement, and evidence freshness

All scores are normalized to `0-100`.

## Input Strategy
The product now separates:
- manual quick-triage inputs that a human can gather quickly
- future automated enrichment that may come from online research or LLM-assisted synthesis

Current manual inputs are limited to a small set of factual fields:
- company name
- latest funding round if known
- approximate team size if known
- current engineering leadership layer
- rough hiring counts
- optional links and freeform notes

Signals that require heavier research or subjective judgment should not be manually entered in v1. If they are used later, they should be populated by an automated research layer or derived from stronger evidence.

## Signal Catalog
Every signal has:
- source type
- freshness window in days
- missing-data effect
- scoring impact

### Company Fundamentals
| Signal | Source Type | Freshness | Missing Data | Direction | Weight | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `stage` | manual quick-triage or public funding source | 730 | neutral | fit positive for Seed to Series C | 6 | Mid-stage startups often need leadership layers to scale. |
| `team_size_band` | manual quick-triage or public company profile | 365 | lowers confidence | fit positive for 40-250 employees | 8 | Companies that are too small or too large are less likely to fit the target hiring pattern. |
| `employee_growth` | future automated research | 180 | lowers confidence | fit positive for strong growth, risk positive for decline | 10 | Headcount acceleration is a leading indicator of organizational complexity. |
| `product_complexity` | derived or future automated research | 365 | lowers confidence | fit positive | 6 | Multi-product or platform companies need stronger engineering leadership. |
| `engineering_intensity` | derived or future automated research | 180 | lowers confidence | fit positive | 8 | Large engineering scope often precedes executive layering. |

### Leadership Setup
| Signal | Source Type | Freshness | Missing Data | Direction | Weight | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `founder_setup` | future automated research | 365 | lowers confidence | fit positive for non-technical founders | 7 | Non-technical founding teams often need stronger R&D leadership earlier. |
| `existing_exec_layer` | manual quick-triage or leadership page | 120 | lowers confidence | fit negative if strong CTO/VP Eng exists | 14 | A mature executive layer reduces near-term need. |
| `leadership_gap` | derived from multiple signals, not direct manual input | 120 | lowers confidence | fit positive | 14 | Clear gap between founders/directors and org scale is one of the strongest triggers. |
| `senior_churn` | future automated research | 180 | lowers confidence | risk positive | 12 | Senior instability can indicate opportunity risk or replacement dynamics. |

### Market and Activity Signals
| Signal | Source Type | Freshness | Missing Data | Direction | Weight | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `recent_funding` | future automated research | 240 | neutral | fit positive | 10 | New capital often funds org build-out. |
| `recent_news_momentum` | derived or future automated research | 120 | lowers confidence | fit positive for expansion signals, risk positive for negative news | 7 | Expansion and market traction support leadership investment. |
| `hiring_volume` | manual quick-triage or careers page | 60 | lowers confidence | fit positive for broad hiring | 9 | Hiring acceleration signals scaling pressure. |
| `engineering_hiring_mix` | manual quick-triage or careers page | 60 | lowers confidence | fit positive for engineering-heavy mix | 10 | Engineering-heavy growth supports a VP R&D need. |
| `senior_hiring_signal` | future automated research | 90 | lowers confidence | fit positive | 8 | Senior-function build-out often happens in parallel with executive layering. |
| `geo_expansion` | future automated research | 180 | lowers confidence | fit positive | 5 | Multi-site growth increases coordination demands. |

### Risk Signals
| Signal | Source Type | Freshness | Missing Data | Direction | Weight | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `layoff_signal` | future automated research | 240 | neutral | risk positive | 16 | Layoffs strongly reduce opportunity quality. |
| `funding_slowdown` | derived or future automated research | 365 | lowers confidence | risk positive | 10 | Stalled financing can freeze senior hiring. |
| `hiring_freeze_signal` | future automated research | 90 | lowers confidence | risk positive | 13 | A hiring freeze is a direct warning signal. |
| `founder_instability` | future automated research | 180 | lowers confidence | risk positive | 12 | Founder churn or conflict reduces attractiveness. |
| `pmf_uncertainty` | derived or future automated research | 180 | lowers confidence | risk positive | 8 | Weak traction reduces leadership hiring urgency. |

## Confidence Rules
Confidence combines:
- coverage of core quick-triage fields
- evidence freshness
- optional enrichment breadth
- source agreement

Baseline confidence should not assume a human will populate the full signal catalog manually. It is anchored to the core quick-triage fields and then adjusted:
- subtract for stale evidence on populated core signals
- subtract for source conflicts
- add a small bonus when enrichment adds additional supported signals
- avoid penalizing the user simply because automated-research-only fields are still empty

## Recommendation Thresholds
- `Pursue now`: fit >= 65, risk <= 45, confidence >= 55
- `Monitor`: fit >= 45 and confidence >= 40, unless risk >= 70
- `Low priority`: otherwise

## Explanation Rules
The explanation must:
- reference the strongest positive signals
- reference the strongest risk signals if present
- mention low confidence when applicable
- avoid unsupported speculation
- map recommendation directly to scores
