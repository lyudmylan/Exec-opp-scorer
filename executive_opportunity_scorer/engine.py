from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Iterable

from .models import CompanyInput, Evidence, ScoreResult, SignalResult, parse_iso_date
from .rules import SIGNAL_RULES

CORE_CONFIDENCE_SIGNALS = (
    "stage",
    "team_size_band",
    "existing_exec_layer",
    "hiring_volume",
    "engineering_hiring_mix",
)


def clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return int(round(max(minimum, min(maximum, value))))


def score_company(company: CompanyInput) -> ScoreResult:
    _validate_scope(company)

    signals = [
        _score_stage(company),
        _score_team_size(company),
        _score_employee_growth(company),
        _score_product_complexity(company),
        _score_engineering_intensity(company),
        _score_founder_setup(company),
        _score_existing_exec_layer(company),
        _score_leadership_gap(company),
        _score_senior_churn(company),
        _score_recent_funding(company),
        _score_recent_news(company),
        _score_hiring_volume(company),
        _score_engineering_hiring_mix(company),
        _score_senior_hiring(company),
        _score_geo_expansion(company),
        _score_layoffs(company),
        _score_funding_slowdown(company),
        _score_hiring_freeze(company),
        _score_founder_instability(company),
        _score_pmf_uncertainty(company),
    ]

    fit_raw = 30.0 + sum(signal.fit_delta for signal in signals)
    risk_raw = 15.0 + sum(signal.risk_delta for signal in signals)
    confidence = _compute_confidence(company, signals)

    fit_score = clamp(fit_raw)
    risk_score = clamp(risk_raw)
    recommendation = _recommend(fit_score, risk_score, confidence, signals)
    positive_signals = _top_summaries(signals, positive=True)
    risk_signals = _top_summaries(signals, positive=False)
    blockers = _top_blockers(signals)
    explanation = _build_explanation(company, fit_score, risk_score, confidence, recommendation, positive_signals, risk_signals, blockers)
    next_steps = _build_next_steps(recommendation, confidence, risk_score)

    sources = list(_unique_sources(company.evidence.values()))
    return ScoreResult(
        company_name=company.company_name,
        snapshot_date=company.snapshot_date,
        fit_score=fit_score,
        risk_score=risk_score,
        confidence=confidence,
        recommendation=recommendation,
        explanation=explanation,
        next_steps=next_steps,
        top_positive_signals=positive_signals,
        top_risk_signals=risk_signals,
        fired_signals=signals,
        sources_used=sources,
    )


def _validate_scope(company: CompanyInput) -> None:
    if company.geography.strip().lower() != "israel":
        raise ValueError("Only Israeli companies are supported in v1.")
    if company.category.strip().lower() != "saas":
        raise ValueError("Only SaaS companies are supported in v1.")
    if company.is_gray_area:
        raise ValueError("Gray-area companies are excluded from scoring.")


def _signal(name: str, value, fit_delta: float, risk_delta: float, confidence_delta: float, evidence_count: int, summary: str) -> SignalResult:
    return SignalResult(
        name=name,
        category=SIGNAL_RULES[name].category,
        value=value,
        fit_delta=fit_delta,
        risk_delta=risk_delta,
        confidence_delta=confidence_delta,
        evidence_count=evidence_count,
        summary=summary,
    )


def _freshness_multiplier(company: CompanyInput, signal_name: str) -> tuple[float, int]:
    evidence_items = company.evidence.get(signal_name, [])
    if not evidence_items:
        return 0.0, 0

    snapshot = parse_iso_date(company.snapshot_date)
    max_age = SIGNAL_RULES[signal_name].max_age_days
    freshest = min((snapshot - parse_iso_date(item.observed_at)).days for item in evidence_items)
    if freshest <= max_age:
        return 1.0, len(evidence_items)
    if freshest <= max_age * 2:
        return 0.5, len(evidence_items)
    return 0.0, len(evidence_items)


def _staleness_penalty(company: CompanyInput, signal_name: str) -> float:
    multiplier, count = _freshness_multiplier(company, signal_name)
    if count == 0:
        return -4.0 if SIGNAL_RULES[signal_name].weight >= 10 else -2.0
    if multiplier == 0.5:
        return -2.0
    if multiplier == 0.0:
        return -4.0
    return 1.0 if count >= 2 else 0.0


def _weighted(name: str, intensity: float, positive_summary: str, negative_summary: str | None = None) -> tuple[float, str]:
    if intensity > 0:
        return SIGNAL_RULES[name].weight * intensity, positive_summary
    if intensity < 0:
        summary = negative_summary or positive_summary
        return SIGNAL_RULES[name].weight * intensity, summary
    return 0.0, "No material signal."


def _score_stage(company: CompanyInput) -> SignalResult:
    stage = (company.company_stage or "").lower()
    intensity = 0.0
    if stage in {"series b", "series c"}:
        intensity = 1.0
    elif stage == "series a":
        intensity = 0.7
    elif stage in {"seed", "pre-seed"}:
        intensity = 0.2
    elif stage in {"series d", "growth", "public"}:
        intensity = -0.4
    fit_delta, summary = _weighted("stage", intensity, f"Stage `{company.company_stage}` supports leadership build-out.", "Stage suggests the company may already be past the typical VP R&D inflection.")
    return _signal("stage", company.company_stage, fit_delta, 0.0, _staleness_penalty(company, "stage"), len(company.evidence.get("stage", [])), summary)


def _score_team_size(company: CompanyInput) -> SignalResult:
    size = company.team_size
    intensity = 0.0
    if size is not None:
        if 40 <= size <= 250:
            intensity = 1.0
        elif 20 <= size < 40 or 251 <= size <= 400:
            intensity = 0.3
        else:
            intensity = -0.5
    fit_delta, summary = _weighted("team_size_band", intensity, "Team size sits in the likely VP R&D hiring band.", "Team size is outside the strongest VP R&D hiring band.")
    return _signal("team_size_band", size, fit_delta, 0.0, _staleness_penalty(company, "team_size_band"), len(company.evidence.get("team_size_band", [])), summary)


def _score_employee_growth(company: CompanyInput) -> SignalResult:
    growth = company.employee_growth_6m_pct
    intensity = 0.0
    risk_delta = 0.0
    summary = "No material signal."
    if growth is not None:
        if growth >= 25:
            intensity = 1.0
            summary = "Employee growth is strong, suggesting scaling pressure."
        elif growth >= 10:
            intensity = 0.5
            summary = "Employee growth is positive and supports a scaling narrative."
        elif growth <= -10:
            risk_delta = SIGNAL_RULES["employee_growth"].weight * 0.8
            intensity = -0.4
            summary = "Employee decline raises caution about growth quality."
    fit_delta = SIGNAL_RULES["employee_growth"].weight * intensity
    return _signal("employee_growth", growth, fit_delta, risk_delta, _staleness_penalty(company, "employee_growth"), len(company.evidence.get("employee_growth", [])), summary)


def _score_product_complexity(company: CompanyInput) -> SignalResult:
    mapping = {"high": 1.0, "medium": 0.4, "low": -0.2}
    value = (company.product_complexity or "").lower()
    fit_delta, summary = _weighted("product_complexity", mapping.get(value, 0.0), "Product complexity supports dedicated R&D leadership.", "Lower product complexity weakens the case for a VP R&D hire.")
    return _signal("product_complexity", company.product_complexity, fit_delta, 0.0, _staleness_penalty(company, "product_complexity"), len(company.evidence.get("product_complexity", [])), summary)


def _score_engineering_intensity(company: CompanyInput) -> SignalResult:
    mapping = {"high": 1.0, "medium": 0.4, "low": -0.3}
    value = (company.engineering_intensity or "").lower()
    fit_delta, summary = _weighted("engineering_intensity", mapping.get(value, 0.0), "Engineering intensity is high enough to justify stronger R&D leadership.", "Engineering intensity appears limited for a dedicated VP R&D role.")
    return _signal("engineering_intensity", company.engineering_intensity, fit_delta, 0.0, _staleness_penalty(company, "engineering_intensity"), len(company.evidence.get("engineering_intensity", [])), summary)


def _score_founder_setup(company: CompanyInput) -> SignalResult:
    mapping = {
        "non_technical": 1.0,
        "mixed": 0.1,
        "technical": -1.0,
    }
    value = (company.founder_setup or "").lower()
    fit_delta, summary = _weighted("founder_setup", mapping.get(value, 0.0), "Founder setup increases need for dedicated R&D leadership.", "Technical founder coverage reduces urgency for an external VP R&D hire.")
    return _signal("founder_setup", company.founder_setup, fit_delta, 0.0, _staleness_penalty(company, "founder_setup"), len(company.evidence.get("founder_setup", [])), summary)


def _score_existing_exec_layer(company: CompanyInput) -> SignalResult:
    mapping = {
        "none": 1.0,
        "partial": -0.4,
        "strong": -1.2,
    }
    value = (company.existing_exec_layer or "").lower()
    fit_delta, summary = _weighted("existing_exec_layer", mapping.get(value, 0.0), "There is no mature R&D executive layer in place.", "A strong existing CTO or VP Eng layer lowers near-term need.")
    return _signal("existing_exec_layer", company.existing_exec_layer, fit_delta, 0.0, _staleness_penalty(company, "existing_exec_layer"), len(company.evidence.get("existing_exec_layer", [])), summary)


def _score_leadership_gap(company: CompanyInput) -> SignalResult:
    mapping = {"high": 1.0, "medium": 0.5, "low": -0.8}
    value = (company.leadership_gap or "").lower()
    fit_delta, summary = _weighted("leadership_gap", mapping.get(value, 0.0), "The current org appears to have a leadership gap that a VP R&D could fill.", "Leadership layering already looks relatively mature.")
    return _signal("leadership_gap", company.leadership_gap, fit_delta, 0.0, _staleness_penalty(company, "leadership_gap"), len(company.evidence.get("leadership_gap", [])), summary)


def _score_senior_churn(company: CompanyInput) -> SignalResult:
    mapping = {"high": 1.0, "medium": 0.5, "low": 0.0, "none": 0.0}
    value = (company.senior_churn or "").lower()
    risk_delta, summary = _weighted("senior_churn", mapping.get(value, 0.0), "Senior churn increases opportunity risk.")
    return _signal("senior_churn", company.senior_churn, 0.0, max(risk_delta, 0.0), _staleness_penalty(company, "senior_churn"), len(company.evidence.get("senior_churn", [])), summary)


def _score_recent_funding(company: CompanyInput) -> SignalResult:
    months = company.recent_funding_months_ago
    intensity = 0.0
    if months is not None:
        if months <= 9:
            intensity = 1.0
        elif months <= 18:
            intensity = 0.4
        elif months > 36:
            intensity = -0.2
    fit_delta, summary = _weighted("recent_funding", intensity, "Recent funding supports leadership expansion.", "Funding is not recent enough to strongly support a near-term VP R&D hire.")
    return _signal("recent_funding", months, fit_delta, 0.0, _staleness_penalty(company, "recent_funding"), len(company.evidence.get("recent_funding", [])), summary)


def _score_recent_news(company: CompanyInput) -> SignalResult:
    value = (company.recent_news_sentiment or "").lower()
    fit_delta = 0.0
    risk_delta = 0.0
    summary = "No material signal."
    if value == "positive":
        fit_delta = SIGNAL_RULES["recent_news_momentum"].weight * 0.6
        summary = "Recent news momentum supports company expansion."
    elif value == "mixed":
        fit_delta = SIGNAL_RULES["recent_news_momentum"].weight * 0.3
        risk_delta = SIGNAL_RULES["recent_news_momentum"].weight * 0.2
        summary = "Recent news is mixed, suggesting both momentum and uncertainty."
    elif value == "negative":
        risk_delta = SIGNAL_RULES["recent_news_momentum"].weight * 0.8
        summary = "Recent negative news increases opportunity risk."
    return _signal("recent_news_momentum", company.recent_news_sentiment, fit_delta, risk_delta, _staleness_penalty(company, "recent_news_momentum"), len(company.evidence.get("recent_news_momentum", [])), summary)


def _score_hiring_volume(company: CompanyInput) -> SignalResult:
    roles = company.hiring_open_roles
    intensity = 0.0
    if roles is not None:
        if roles >= 12:
            intensity = 1.0
        elif roles >= 5:
            intensity = 0.5
        elif roles == 0:
            intensity = -0.4
    fit_delta, summary = _weighted("hiring_volume", intensity, "Overall hiring volume suggests scaling pressure.", "Low hiring volume weakens the case for near-term executive expansion.")
    return _signal("hiring_volume", roles, fit_delta, 0.0, _staleness_penalty(company, "hiring_volume"), len(company.evidence.get("hiring_volume", [])), summary)


def _score_engineering_hiring_mix(company: CompanyInput) -> SignalResult:
    total = company.hiring_open_roles
    engineering = company.engineering_roles_open
    intensity = 0.0
    if total is not None and engineering is not None and total > 0:
        ratio = engineering / total
        if ratio >= 0.45 and engineering >= 6:
            intensity = 1.0
        elif ratio >= 0.25:
            intensity = 0.4
        elif engineering == 0:
            intensity = -0.5
    fit_delta, summary = _weighted("engineering_hiring_mix", intensity, "Engineering-heavy hiring mix supports a VP R&D need.", "Current hiring mix is not engineering-heavy enough to strongly support a VP R&D hire.")
    return _signal("engineering_hiring_mix", engineering, fit_delta, 0.0, _staleness_penalty(company, "engineering_hiring_mix"), len(company.evidence.get("engineering_hiring_mix", [])), summary)


def _score_senior_hiring(company: CompanyInput) -> SignalResult:
    roles = company.senior_roles_open
    intensity = 0.0
    if roles is not None:
        if roles >= 3:
            intensity = 1.0
        elif roles >= 1:
            intensity = 0.5
        elif roles == 0:
            intensity = -0.3
    fit_delta, summary = _weighted("senior_hiring_signal", intensity, "Senior function build-out suggests organizational maturation.", "No senior hiring signal is visible yet.")
    return _signal("senior_hiring_signal", roles, fit_delta, 0.0, _staleness_penalty(company, "senior_hiring_signal"), len(company.evidence.get("senior_hiring_signal", [])), summary)


def _score_geo_expansion(company: CompanyInput) -> SignalResult:
    value = company.geo_expansion
    intensity = 1.0 if value else 0.0
    fit_delta, summary = _weighted("geo_expansion", intensity, "Geographic expansion increases coordination complexity.")
    return _signal("geo_expansion", value, fit_delta, 0.0, _staleness_penalty(company, "geo_expansion"), len(company.evidence.get("geo_expansion", [])), summary)


def _score_layoffs(company: CompanyInput) -> SignalResult:
    mapping = {"high": 1.0, "medium": 0.6, "low": 0.3, "none": 0.0}
    value = (company.layoff_signal or "").lower()
    risk_delta, summary = _weighted("layoff_signal", mapping.get(value, 0.0), "Layoff signals materially raise opportunity risk.")
    return _signal("layoff_signal", company.layoff_signal, 0.0, max(risk_delta, 0.0), _staleness_penalty(company, "layoff_signal"), len(company.evidence.get("layoff_signal", [])), summary)


def _score_funding_slowdown(company: CompanyInput) -> SignalResult:
    mapping = {"high": 1.0, "medium": 0.5, "low": 0.2, "none": 0.0}
    value = (company.funding_slowdown or "").lower()
    risk_delta, summary = _weighted("funding_slowdown", mapping.get(value, 0.0), "Funding slowdown reduces confidence in leadership hiring.")
    return _signal("funding_slowdown", company.funding_slowdown, 0.0, max(risk_delta, 0.0), _staleness_penalty(company, "funding_slowdown"), len(company.evidence.get("funding_slowdown", [])), summary)


def _score_hiring_freeze(company: CompanyInput) -> SignalResult:
    mapping = {"high": 1.0, "medium": 0.5, "low": 0.2, "none": 0.0}
    value = (company.hiring_freeze_signal or "").lower()
    risk_delta, summary = _weighted("hiring_freeze_signal", mapping.get(value, 0.0), "Hiring freeze signals reduce near-term opportunity quality.")
    return _signal("hiring_freeze_signal", company.hiring_freeze_signal, 0.0, max(risk_delta, 0.0), _staleness_penalty(company, "hiring_freeze_signal"), len(company.evidence.get("hiring_freeze_signal", [])), summary)


def _score_founder_instability(company: CompanyInput) -> SignalResult:
    mapping = {"high": 1.0, "medium": 0.5, "low": 0.2, "none": 0.0}
    value = (company.founder_instability or "").lower()
    risk_delta, summary = _weighted("founder_instability", mapping.get(value, 0.0), "Founder instability makes the opportunity less attractive.")
    return _signal("founder_instability", company.founder_instability, 0.0, max(risk_delta, 0.0), _staleness_penalty(company, "founder_instability"), len(company.evidence.get("founder_instability", [])), summary)


def _score_pmf_uncertainty(company: CompanyInput) -> SignalResult:
    mapping = {"high": 1.0, "medium": 0.5, "low": 0.2, "none": 0.0}
    value = (company.pmf_uncertainty or "").lower()
    risk_delta, summary = _weighted("pmf_uncertainty", mapping.get(value, 0.0), "Unclear product-market fit raises opportunity risk.")
    return _signal("pmf_uncertainty", company.pmf_uncertainty, 0.0, max(risk_delta, 0.0), _staleness_penalty(company, "pmf_uncertainty"), len(company.evidence.get("pmf_uncertainty", [])), summary)


def _compute_confidence(company: CompanyInput, signals: list[SignalResult]) -> int:
    signal_map = {signal.name: signal for signal in signals}
    populated_core = sum(
        1
        for name in CORE_CONFIDENCE_SIGNALS
        if signal_map[name].value not in (None, "", [])
    )
    baseline = 35.0 + (45.0 * (populated_core / len(CORE_CONFIDENCE_SIGNALS)))
    freshness_adjustment = sum(
        signal_map[name].confidence_delta
        for name in CORE_CONFIDENCE_SIGNALS
        if signal_map[name].value not in (None, "", [])
    )
    enrichment_bonus = min(
        10.0,
        2.0
        * sum(
            1
            for signal in signals
            if signal.name not in CORE_CONFIDENCE_SIGNALS
            and signal.value not in (None, "", [])
        ),
    )
    conflict_penalty = _source_conflict_penalty(company)
    return clamp(baseline + freshness_adjustment + enrichment_bonus - conflict_penalty)


def _source_conflict_penalty(company: CompanyInput) -> float:
    penalty = 0.0
    for items in company.evidence.values():
        distinct_notes = {item.note.strip().lower() for item in items if item.note.strip()}
        if len(distinct_notes) >= 3:
            penalty += 2.0
    return penalty


def _recommend(fit_score: int, risk_score: int, confidence: int, signals: list[SignalResult]) -> str:
    strongest_blocker = max((-signal.fit_delta for signal in signals if signal.fit_delta < 0), default=0.0)
    if fit_score >= 65 and risk_score <= 45 and confidence >= 55 and strongest_blocker < 12:
        return "Pursue now"
    if fit_score >= 45 and confidence >= 40 and risk_score < 70:
        return "Monitor"
    return "Low priority"


def _top_summaries(signals: list[SignalResult], positive: bool) -> list[str]:
    if positive:
        ranked = sorted((signal for signal in signals if signal.fit_delta > 0), key=lambda item: item.fit_delta, reverse=True)
    else:
        ranked = sorted((signal for signal in signals if signal.risk_delta > 0), key=lambda item: item.risk_delta, reverse=True)
    return [signal.summary for signal in ranked[:3]]


def _top_blockers(signals: list[SignalResult]) -> list[str]:
    ranked = sorted((signal for signal in signals if signal.fit_delta < 0), key=lambda item: item.fit_delta)
    return [signal.summary for signal in ranked[:2]]


def _build_explanation(company: CompanyInput, fit_score: int, risk_score: int, confidence: int, recommendation: str, positive_signals: list[str], risk_signals: list[str], blockers: list[str]) -> str:
    positives = "; ".join(positive_signals) if positive_signals else "few strong positive signals were found"
    risks = "; ".join(risk_signals) if risk_signals else "few major risk signals were found"
    blockers_text = f" Main blockers: {'; '.join(blockers)}." if blockers else ""
    confidence_clause = "Evidence coverage is limited, so this should be treated as directional." if confidence < 50 else "Evidence coverage is solid enough for an initial decision."
    return (
        f"{company.company_name} is scored as `{recommendation}` with fit {fit_score}, risk {risk_score}, and confidence {confidence}. "
        f"Main positives: {positives}. Main risks: {risks}.{blockers_text} {confidence_clause}"
    )


def _build_next_steps(recommendation: str, confidence: int, risk_score: int) -> list[str]:
    if recommendation == "Pursue now":
        steps = [
            "Prioritize outreach to founders or the current engineering leader within the next 2 weeks.",
            "Validate the leadership gap directly in conversations and recent org updates.",
            "Prepare a hypothesis on how you would scale the R&D organization over the next 12 months.",
        ]
    elif recommendation == "Monitor":
        steps = [
            "Track funding, senior hiring, and engineering hiring changes over the next 60-90 days.",
            "Set a trigger for renewed review if leadership departures or expansion signals appear.",
            "Do light networking now, but defer heavy outreach until evidence strengthens.",
        ]
    else:
        steps = [
            "Do not prioritize outreach now.",
            "Revisit only if a new funding round, leadership gap, or hiring expansion appears.",
            "Use this company as a comparison case for calibration rather than an immediate target.",
        ]
    if confidence < 50:
        steps.append("Collect additional public evidence before making a high-conviction decision.")
    if risk_score >= 70:
        steps.append("Treat risk as a gating factor even if future growth signals improve.")
    return steps


def _unique_sources(groups: Iterable[list[Evidence]]) -> Iterable[Evidence]:
    seen: set[tuple[str, str, str]] = set()
    for items in groups:
        for item in items:
            key = (item.url, item.observed_at, item.label)
            if key in seen:
                continue
            seen.add(key)
            yield item


def score_to_dict(result: ScoreResult) -> dict:
    payload = asdict(result)
    payload["sources_used"] = [asdict(item) for item in result.sources_used]
    payload["fired_signals"] = [asdict(item) for item in result.fired_signals]
    return payload
