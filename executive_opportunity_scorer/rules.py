from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SignalRule:
    category: str
    weight: float
    max_age_days: int
    description: str


SIGNAL_RULES: dict[str, SignalRule] = {
    "stage": SignalRule("fundamentals", 6.0, 730, "Mid-stage companies are more likely to need a VP R&D."),
    "team_size_band": SignalRule("fundamentals", 8.0, 365, "R&D leadership need rises in the 40-250 employee band."),
    "employee_growth": SignalRule("fundamentals", 10.0, 180, "Fast headcount growth raises organizational complexity."),
    "product_complexity": SignalRule("fundamentals", 6.0, 365, "More complex products need stronger engineering coordination."),
    "engineering_intensity": SignalRule("fundamentals", 8.0, 180, "Engineering-heavy organizations benefit from dedicated R&D leadership."),
    "founder_setup": SignalRule("leadership", 7.0, 365, "Non-technical founders increase need for engineering leadership."),
    "existing_exec_layer": SignalRule("leadership", 14.0, 120, "A strong current CTO or VP Eng reduces near-term need."),
    "leadership_gap": SignalRule("leadership", 14.0, 120, "A gap between company size and current leadership strongly raises need."),
    "senior_churn": SignalRule("leadership", 12.0, 180, "Senior churn is a meaningful risk signal."),
    "recent_funding": SignalRule("activity", 10.0, 240, "Recent funding often supports leadership build-out."),
    "recent_news_momentum": SignalRule("activity", 7.0, 120, "Expansion news is a positive sign while negative news raises risk."),
    "hiring_volume": SignalRule("activity", 9.0, 60, "Broad hiring indicates scaling pressure."),
    "engineering_hiring_mix": SignalRule("activity", 10.0, 60, "Engineering-heavy hiring mix supports VP R&D demand."),
    "senior_hiring_signal": SignalRule("activity", 8.0, 90, "Senior hiring can precede executive layering."),
    "geo_expansion": SignalRule("activity", 5.0, 180, "Geographic expansion adds management complexity."),
    "layoff_signal": SignalRule("risk", 16.0, 240, "Layoffs are a strong opportunity risk signal."),
    "funding_slowdown": SignalRule("risk", 10.0, 365, "Funding slowdown can block executive hiring."),
    "hiring_freeze_signal": SignalRule("risk", 13.0, 90, "Hiring freezes strongly reduce near-term opportunity quality."),
    "founder_instability": SignalRule("risk", 12.0, 180, "Founder instability makes the opportunity less attractive."),
    "pmf_uncertainty": SignalRule("risk", 8.0, 180, "Weak product-market fit reduces confidence in expansion."),
}
