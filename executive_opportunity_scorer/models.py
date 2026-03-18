from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Evidence:
    source_type: str
    label: str
    url: str
    observed_at: str
    published_at: str | None = None
    note: str = ""


@dataclass(slots=True)
class CompanyInput:
    company_name: str
    snapshot_date: str
    geography: str
    category: str
    is_gray_area: bool
    company_url: str | None = None
    research_notes: str | None = None
    source_urls_text: str | None = None
    current_engineering_leadership: list[str] | None = None
    approx_rd_size: int | None = None
    company_stage: str | None = None
    team_size: int | None = None
    founder_setup: str | None = None
    product_complexity: str | None = None
    engineering_intensity: str | None = None
    employee_growth_6m_pct: float | None = None
    recent_funding_months_ago: int | None = None
    recent_news_sentiment: str | None = None
    hiring_open_roles: int | None = None
    engineering_roles_open: int | None = None
    senior_roles_open: int | None = None
    geo_expansion: bool | None = None
    existing_exec_layer: str | None = None
    leadership_gap: str | None = None
    senior_churn: str | None = None
    layoff_signal: str | None = None
    funding_slowdown: str | None = None
    hiring_freeze_signal: str | None = None
    founder_instability: str | None = None
    pmf_uncertainty: str | None = None
    evidence: dict[str, list[Evidence]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CompanyInput":
        evidence_payload = payload.get("evidence", {})
        evidence = {
            key: [Evidence(**item) for item in items]
            for key, items in evidence_payload.items()
        }
        base = {key: value for key, value in payload.items() if key != "evidence"}
        return cls(evidence=evidence, **base)


@dataclass(slots=True)
class SignalResult:
    name: str
    category: str
    value: Any
    fit_delta: float
    risk_delta: float
    confidence_delta: float
    evidence_count: int
    summary: str


@dataclass(slots=True)
class ScoreResult:
    company_name: str
    snapshot_date: str
    fit_score: int
    risk_score: int
    confidence: int
    recommendation: str
    explanation: str
    next_steps: list[str]
    top_positive_signals: list[str]
    top_risk_signals: list[str]
    fired_signals: list[SignalResult]
    sources_used: list[Evidence]


def parse_iso_date(value: str) -> date:
    if "T" in value:
        return datetime.fromisoformat(value).date()
    return date.fromisoformat(value)
