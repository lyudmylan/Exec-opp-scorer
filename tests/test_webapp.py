from __future__ import annotations

import unittest
from datetime import datetime

from executive_opportunity_scorer.webapp import build_template_from_spec, coerce_submission, load_ui_spec


class WebAppTests(unittest.TestCase):
    def test_template_contains_known_keys(self) -> None:
        spec = load_ui_spec()
        template = build_template_from_spec(spec)
        self.assertTrue(template["snapshot_date"].startswith(datetime.now().date().isoformat()))
        self.assertEqual(template["geography"], "Israel")
        self.assertEqual(template["category"], "SaaS")
        self.assertEqual(template["hiring_open_roles"], None)
        self.assertEqual(template["engineering_roles_open"], None)

    def test_submission_coercion_handles_partial_values(self) -> None:
        spec = load_ui_spec()
        payload = {
            "company_name": "TestCo",
            "team_size": "120",
            "source_urls_text": "https://example.com/testco-headcount",
            "current_engineering_leadership": ["Co-Founder & CTO", "VP Engineering"],
        }
        normalized = coerce_submission(spec, payload)
        self.assertTrue(normalized["snapshot_date"].startswith(datetime.now().date().isoformat()))
        self.assertEqual(normalized["team_size"], 120)
        self.assertEqual(normalized["source_urls_text"], "https://example.com/testco-headcount")
        self.assertEqual(normalized["existing_exec_layer"], "strong")
        self.assertEqual(normalized["current_engineering_leadership"], ["Co-Founder & CTO", "VP Engineering"])

    def test_submission_requires_mandatory_fields(self) -> None:
        spec = load_ui_spec()
        with self.assertRaisesRegex(Exception, "company_name"):
            coerce_submission(
                spec,
                {
                    "company_stage": "Series A",
                },
            )

    def test_single_founder_cto_maps_to_partial_exec_layer(self) -> None:
        spec = load_ui_spec()
        normalized = coerce_submission(
            spec,
            {
                "company_name": "FounderLedCo",
                "current_engineering_leadership": ["Co-Founder & CTO"],
            },
        )
        self.assertEqual(normalized["existing_exec_layer"], "partial")

    def test_single_cto_maps_to_strong_exec_layer(self) -> None:
        spec = load_ui_spec()
        normalized = coerce_submission(
            spec,
            {
                "company_name": "ExecCo",
                "current_engineering_leadership": ["CTO"],
            },
        )
        self.assertEqual(normalized["existing_exec_layer"], "strong")

    def test_standalone_vp_engineering_maps_to_partial_exec_layer(self) -> None:
        spec = load_ui_spec()
        normalized = coerce_submission(
            spec,
            {
                "company_name": "VpLedCo",
                "current_engineering_leadership": ["VP Engineering"],
            },
        )
        self.assertEqual(normalized["existing_exec_layer"], "partial")

    def test_standalone_head_of_engineering_maps_to_partial_exec_layer(self) -> None:
        spec = load_ui_spec()
        normalized = coerce_submission(
            spec,
            {
                "company_name": "HeadLedCo",
                "current_engineering_leadership": ["Head of Engineering"],
            },
        )
        self.assertEqual(normalized["existing_exec_layer"], "partial")

    def test_founder_cto_plus_head_maps_to_strong_exec_layer(self) -> None:
        spec = load_ui_spec()
        normalized = coerce_submission(
            spec,
            {
                "company_name": "ScaledCo",
                "current_engineering_leadership": ["Co-Founder & CTO", "Head of Engineering"],
            },
        )
        self.assertEqual(normalized["existing_exec_layer"], "strong")

    def test_no_engineering_leadership_maps_to_none(self) -> None:
        spec = load_ui_spec()
        normalized = coerce_submission(
            spec,
            {
                "company_name": "OpenSlotCo",
            },
        )
        self.assertEqual(normalized["existing_exec_layer"], "none")


if __name__ == "__main__":
    unittest.main()
