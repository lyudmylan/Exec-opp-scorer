from __future__ import annotations

import unittest
from datetime import date

from executive_opportunity_scorer.webapp import build_template_from_spec, coerce_submission, load_ui_spec


class WebAppTests(unittest.TestCase):
    def test_template_contains_known_keys(self) -> None:
        spec = load_ui_spec()
        template = build_template_from_spec(spec)
        self.assertEqual(template["snapshot_date"], date.today().isoformat())
        self.assertEqual(template["geography"], "Israel")
        self.assertEqual(template["category"], "SaaS")
        self.assertIn("stage", template["evidence"])
        self.assertIn("team_size_band", template["evidence"])

    def test_submission_coercion_handles_partial_values(self) -> None:
        spec = load_ui_spec()
        payload = {
            "company_name": "TestCo",
            "geography": "Israel",
            "category": "SaaS",
            "is_gray_area": False,
            "team_size": "120",
            "source_urls_text": "https://example.com/testco-headcount",
            "evidence": {
                "team_size_band": [
                    {
                        "source_type": "research",
                        "label": "Headcount review",
                        "url": "https://example.com/testco-headcount",
                        "observed_at": "2026-03-10",
                        "note": "Around 120 employees."
                    }
                ]
            }
        }
        normalized = coerce_submission(spec, payload)
        self.assertEqual(normalized["snapshot_date"], date.today().isoformat())
        self.assertEqual(normalized["team_size"], 120)
        self.assertEqual(normalized["source_urls_text"], "https://example.com/testco-headcount")
        self.assertEqual(normalized["evidence"]["team_size_band"][0]["label"], "Headcount review")

    def test_submission_requires_mandatory_fields(self) -> None:
        spec = load_ui_spec()
        with self.assertRaisesRegex(Exception, "company_name"):
            coerce_submission(
                spec,
                {
                    "company_stage": "Series A",
                },
            )

    def test_submission_rejects_incomplete_evidence_rows(self) -> None:
        spec = load_ui_spec()
        with self.assertRaisesRegex(Exception, "observed_at"):
            coerce_submission(
                spec,
                {
                    "company_name": "TestCo",
                    "evidence": {
                        "stage": [
                            {
                                "source_type": "funding",
                                "label": "Funding announcement",
                                "url": "https://example.com/funding"
                            }
                        ]
                    },
                },
            )


if __name__ == "__main__":
    unittest.main()
