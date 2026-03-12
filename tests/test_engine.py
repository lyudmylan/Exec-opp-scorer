from __future__ import annotations

import json
import unittest
from pathlib import Path

from executive_opportunity_scorer.engine import score_company
from executive_opportunity_scorer.models import CompanyInput


SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


def load_sample(name: str) -> CompanyInput:
    payload = json.loads((SAMPLES / name).read_text())
    return CompanyInput.from_dict(payload)


class ExecutiveOpportunityScorerTests(unittest.TestCase):
    def test_growth_case_is_pursue_now(self) -> None:
        result = score_company(load_sample("series_b_growth.json"))
        self.assertEqual(result.recommendation, "Pursue now")
        self.assertGreaterEqual(result.fit_score, 65)
        self.assertLessEqual(result.risk_score, 45)
        self.assertGreaterEqual(result.confidence, 55)

    def test_existing_exec_layer_reduces_fit(self) -> None:
        result = score_company(load_sample("existing_exec_layer.json"))
        self.assertIn(result.recommendation, {"Monitor", "Low priority"})
        self.assertLess(result.fit_score, 70)
        self.assertIn("existing CTO or VP Eng layer lowers near-term need", result.explanation)

    def test_technical_founder_case_is_not_high_priority(self) -> None:
        result = score_company(load_sample("founder_led_technical.json"))
        self.assertIn(result.recommendation, {"Monitor", "Low priority"})
        self.assertLess(result.fit_score, 65)

    def test_growth_with_risk_surfaces_risk_signals(self) -> None:
        result = score_company(load_sample("growth_with_risk.json"))
        self.assertGreaterEqual(result.risk_score, 45)
        self.assertTrue(result.top_risk_signals)
        self.assertIn("risk", result.explanation.lower())

    def test_sparse_data_reduces_confidence(self) -> None:
        result = score_company(load_sample("sparse_data.json"))
        self.assertLess(result.confidence, 50)
        self.assertIn("directional", result.explanation)

    def test_conflicting_sources_penalize_confidence(self) -> None:
        result = score_company(load_sample("conflicting_sources.json"))
        self.assertLess(result.confidence, 80)

    def test_out_of_scope_company_is_rejected(self) -> None:
        payload = json.loads((SAMPLES / "series_b_growth.json").read_text())
        payload["category"] = "Gaming"
        with self.assertRaises(ValueError):
            score_company(CompanyInput.from_dict(payload))


if __name__ == "__main__":
    unittest.main()
