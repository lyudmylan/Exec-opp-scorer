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

## Signal Catalog
Every signal has:
- source type
- freshness window in days
- missing-data effect
- scoring impact

### Company Fundamentals
| Signal | Source Type | Freshness | Missing Data | Direction | Weight | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `stage` | structured input/public funding source | 730 | neutral | fit positive for Seed to Series C | 6 | Mid-stage startups often need leadership layers to scale. |
| `team_size_band` | structured input/public company profile | 365 | lowers confidence | fit positive for 40-250 employees | 8 | Companies that are too small or too large are less likely to fit the target hiring pattern. |
| `employee_growth` | public employee trend/research input | 180 | lowers confidence | fit positive for strong growth, risk positive for decline | 10 | Headcount acceleration is a leading indicator of organizational complexity. |
| `product_complexity` | reviewer or public evidence | 365 | lowers confidence | fit positive | 6 | Multi-product or platform companies need stronger engineering leadership. |
| `engineering_intensity` | jobs, GitHub, product language | 180 | lowers confidence | fit positive | 8 | Large engineering scope often precedes executive layering. |

### Leadership Setup
| Signal | Source Type | Freshness | Missing Data | Direction | Weight | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `founder_setup` | website/LinkedIn-style public profiles | 365 | lowers confidence | fit positive for non-technical founders | 7 | Non-technical founding teams often need stronger R&D leadership earlier. |
| `existing_exec_layer` | leadership page/public profiles | 120 | lowers confidence | fit negative if strong CTO/VP Eng exists | 14 | A mature executive layer reduces near-term need. |
| `leadership_gap` | inferred from org structure | 120 | lowers confidence | fit positive | 14 | Clear gap between founders/directors and org scale is one of the strongest triggers. |
| `senior_churn` | news/public profiles | 180 | lowers confidence | risk positive | 12 | Senior instability can indicate opportunity risk or replacement dynamics. |

### Market and Activity Signals
| Signal | Source Type | Freshness | Missing Data | Direction | Weight | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `recent_funding` | public funding/news | 240 | neutral | fit positive | 10 | New capital often funds org build-out. |
| `recent_news_momentum` | press/news | 120 | lowers confidence | fit positive for expansion signals, risk positive for negative news | 7 | Expansion and market traction support leadership investment. |
| `hiring_volume` | careers page/job boards | 60 | lowers confidence | fit positive for broad hiring | 9 | Hiring acceleration signals scaling pressure. |
| `engineering_hiring_mix` | careers page/job boards | 60 | lowers confidence | fit positive for engineering-heavy mix | 10 | Engineering-heavy growth supports a VP R&D need. |
| `senior_hiring_signal` | jobs/news | 90 | lowers confidence | fit positive | 8 | Senior-function build-out often happens in parallel with executive layering. |
| `geo_expansion` | news/jobs/company site | 180 | lowers confidence | fit positive | 5 | Multi-site growth increases coordination demands. |

### Risk Signals
| Signal | Source Type | Freshness | Missing Data | Direction | Weight | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `layoff_signal` | news/public statements | 240 | neutral | risk positive | 16 | Layoffs strongly reduce opportunity quality. |
| `funding_slowdown` | public funding timeline | 365 | lowers confidence | risk positive | 10 | Stalled financing can freeze senior hiring. |
| `hiring_freeze_signal` | jobs/news | 90 | lowers confidence | risk positive | 13 | A hiring freeze is a direct warning signal. |
| `founder_instability` | news/public signals | 180 | lowers confidence | risk positive | 12 | Founder churn or conflict reduces attractiveness. |
| `pmf_uncertainty` | news/reviewer assessment | 180 | lowers confidence | risk positive | 8 | Weak traction reduces leadership hiring urgency. |

## Confidence Rules
Confidence combines:
- field coverage
- evidence freshness
- evidence presence for high-weight signals
- source agreement

Baseline confidence is the ratio of populated signals over total tracked signals. It is then adjusted:
- subtract for stale evidence
- subtract for source conflicts
- subtract when high-weight signals are missing
- add a small bonus when multiple fresh sources agree

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
