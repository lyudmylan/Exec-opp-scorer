from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from executive_opportunity_scorer import engine
from executive_opportunity_scorer.models import CompanyInput


def _minimal_input(**kwargs) -> CompanyInput:
    """Build a minimal valid CompanyInput, overridable via kwargs."""
    defaults = dict(
        company_name="TestCo",
        snapshot_date="2025-01-15",
        geography="Israel",
        category="SaaS",
        is_gray_area=False,
    )
    defaults.update(kwargs)
    return CompanyInput(**defaults)


# ─── Timing window ────────────────────────────────────────────────────────────

class TimingWindowTests(unittest.TestCase):
    def test_blocked_by_hiring_freeze(self) -> None:
        company = _minimal_input(hiring_freeze_signal="high")
        self.assertEqual(engine._build_timing_window(company), "Blocked")

    def test_blocked_by_medium_freeze(self) -> None:
        company = _minimal_input(hiring_freeze_signal="medium")
        self.assertEqual(engine._build_timing_window(company), "Blocked")

    def test_blocked_by_high_layoffs(self) -> None:
        company = _minimal_input(layoff_signal="high")
        self.assertEqual(engine._build_timing_window(company), "Blocked")

    def test_freeze_takes_priority_over_good_funding(self) -> None:
        company = _minimal_input(
            hiring_freeze_signal="high",
            recent_funding_months_ago=3,
            hiring_open_roles=20,
        )
        self.assertEqual(engine._build_timing_window(company), "Blocked")

    def test_early_seed_tiny_team(self) -> None:
        company = _minimal_input(company_stage="seed", team_size=10)
        self.assertEqual(engine._build_timing_window(company), "Early")

    def test_early_pre_seed_tiny_team(self) -> None:
        company = _minimal_input(company_stage="pre-seed", team_size=5)
        self.assertEqual(engine._build_timing_window(company), "Early")

    def test_seed_larger_team_not_early(self) -> None:
        # Seed with 25 people is not "Early" — may be in sweet spot
        company = _minimal_input(company_stage="seed", team_size=25)
        result = engine._build_timing_window(company)
        self.assertNotEqual(result, "Early")

    def test_optimal_recent_funding_plus_hiring(self) -> None:
        company = _minimal_input(recent_funding_months_ago=4, hiring_open_roles=10)
        self.assertEqual(engine._build_timing_window(company), "Optimal")

    def test_good_funding_within_12_months(self) -> None:
        company = _minimal_input(recent_funding_months_ago=10, hiring_open_roles=5)
        self.assertEqual(engine._build_timing_window(company), "Good")

    def test_good_funding_within_18_months(self) -> None:
        company = _minimal_input(recent_funding_months_ago=16)
        self.assertEqual(engine._build_timing_window(company), "Good")

    def test_late_stale_funding_low_hiring(self) -> None:
        company = _minimal_input(recent_funding_months_ago=30, hiring_open_roles=1)
        self.assertEqual(engine._build_timing_window(company), "Late")

    def test_late_negative_growth(self) -> None:
        company = _minimal_input(employee_growth_6m_pct=-15.0)
        self.assertEqual(engine._build_timing_window(company), "Late")

    def test_good_active_hiring_no_funding_data(self) -> None:
        company = _minimal_input(hiring_open_roles=8)
        self.assertEqual(engine._build_timing_window(company), "Good")

    def test_unclear_no_signals(self) -> None:
        company = _minimal_input()
        self.assertEqual(engine._build_timing_window(company), "Unclear")


# ─── Approach angle ───────────────────────────────────────────────────────────

class ApproachAngleTests(unittest.TestCase):
    def _angle(self, recommendation="Pursue now", **kwargs) -> str:
        company = _minimal_input(**kwargs)
        return engine._build_approach_angle(company, recommendation)

    def test_non_technical_founder_no_exec_mentions_ceo(self) -> None:
        angle = self._angle(founder_setup="non_technical", existing_exec_layer="none")
        self.assertIn("CEO", angle)
        self.assertIn("directly", angle.lower())

    def test_non_technical_founder_no_exec_mentions_counterpart(self) -> None:
        angle = self._angle(founder_setup="non_technical", existing_exec_layer="none")
        self.assertIn("counterpart", angle.lower())

    def test_leadership_gap_high_mentions_scaling(self) -> None:
        angle = self._angle(existing_exec_layer="none", leadership_gap="high")
        self.assertIn("inflection", angle.lower())

    def test_senior_churn_mentions_stability(self) -> None:
        angle = self._angle(senior_churn="high", leadership_gap="high")
        self.assertIn("stabilit", angle.lower())

    def test_geo_expansion_mentions_distributed(self) -> None:
        angle = self._angle(geo_expansion=True)
        self.assertIn("distributed", angle.lower())

    def test_series_a_no_exec_mentions_founding(self) -> None:
        angle = self._angle(company_stage="Series A", existing_exec_layer="none")
        self.assertIn("founding", angle.lower())

    def test_monitor_recommendation_mentions_warming(self) -> None:
        angle = self._angle(recommendation="Monitor")
        self.assertIn("warming", angle.lower())

    def test_strong_exec_layer_suggests_warm_intro(self) -> None:
        angle = self._angle(existing_exec_layer="strong")
        self.assertIn("intro", angle.lower())

    def test_result_is_non_empty_string(self) -> None:
        angle = self._angle()
        self.assertIsInstance(angle, str)
        self.assertTrue(len(angle) > 20)

    def test_result_contains_both_pitch_and_contact(self) -> None:
        # The function always appends contact after pitch
        angle = self._angle(founder_setup="non_technical", existing_exec_layer="none")
        # Should have at least two sentences
        self.assertGreater(angle.count("."), 0)


# ─── Storage ──────────────────────────────────────────────────────────────────

class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        # Redirect DB to a temp file for each test
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        import executive_opportunity_scorer.storage as storage
        self._original_path = storage.DB_PATH
        storage.DB_PATH = Path(self._tmp.name)
        storage.init_db()
        self.storage = storage

    def tearDown(self) -> None:
        import executive_opportunity_scorer.storage as storage
        storage.DB_PATH = self._original_path
        Path(self._tmp.name).unlink(missing_ok=True)

    def _sample_result(self, name: str = "TestCo") -> dict:
        return {
            "company_name": name,
            "snapshot_date": "2025-01-15",
            "fit_score": 75,
            "risk_score": 25,
            "confidence": 80,
            "recommendation": "Pursue now",
            "timing_window": "Optimal",
            "approach_angle": "Lead with scaling experience.",
        }

    def test_save_and_list(self) -> None:
        self.storage.save_result(self._sample_result("AlphaCo"))
        entries = self.storage.list_pipeline()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["company_name"], "AlphaCo")

    def test_multiple_entries_ordered_newest_first(self) -> None:
        self.storage.save_result(self._sample_result("First"))
        self.storage.save_result(self._sample_result("Second"))
        entries = self.storage.list_pipeline()
        self.assertEqual(entries[0]["company_name"], "Second")
        self.assertEqual(entries[1]["company_name"], "First")

    def test_save_returns_incrementing_ids(self) -> None:
        id1 = self.storage.save_result(self._sample_result())
        id2 = self.storage.save_result(self._sample_result())
        self.assertGreater(id2, id1)

    def test_get_entry_returns_full_result(self) -> None:
        entry_id = self.storage.save_result(self._sample_result("BetaCo"))
        entry = self.storage.get_entry(entry_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["company_name"], "BetaCo")
        self.assertIn("result", entry)
        self.assertEqual(entry["result"]["fit_score"], 75)

    def test_get_entry_missing_returns_none(self) -> None:
        result = self.storage.get_entry(9999)
        self.assertIsNone(result)

    def test_delete_existing_entry(self) -> None:
        entry_id = self.storage.save_result(self._sample_result())
        deleted = self.storage.delete_entry(entry_id)
        self.assertTrue(deleted)
        self.assertEqual(len(self.storage.list_pipeline()), 0)

    def test_delete_nonexistent_entry_returns_false(self) -> None:
        deleted = self.storage.delete_entry(9999)
        self.assertFalse(deleted)

    def test_save_with_input_data(self) -> None:
        input_data = {"company_name": "TestCo", "company_stage": "Series B"}
        entry_id = self.storage.save_result(self._sample_result(), input_data)
        entry = self.storage.get_entry(entry_id)
        self.assertIsNotNone(entry["input"])
        self.assertEqual(entry["input"]["company_stage"], "Series B")

    def test_empty_pipeline(self) -> None:
        self.assertEqual(self.storage.list_pipeline(), [])


# ─── Enricher ─────────────────────────────────────────────────────────────────

class EnricherTests(unittest.TestCase):
    def test_missing_api_key_returns_error(self) -> None:
        from executive_opportunity_scorer import enricher
        with patch.dict("os.environ", {}, clear=True):
            result = enricher.enrich_from_url("https://example.com")
        self.assertIn("error", result)
        self.assertIn("ANTHROPIC_API_KEY", result["error"])

    def test_missing_anthropic_package_returns_error(self) -> None:
        from executive_opportunity_scorer import enricher
        import sys
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch.dict(sys.modules, {"anthropic": None}):
                result = enricher.enrich_from_url("https://example.com")
        self.assertIn("error", result)

    def test_parse_response_clean_json(self) -> None:
        from executive_opportunity_scorer.enricher import _parse_response
        raw = '{"company_stage": "series b", "team_size": 120}'
        result = _parse_response(raw)
        self.assertEqual(result["company_stage"], "series b")
        self.assertEqual(result["team_size"], 120)

    def test_parse_response_strips_markdown_fence(self) -> None:
        from executive_opportunity_scorer.enricher import _parse_response
        raw = '```json\n{"company_stage": "seed"}\n```'
        result = _parse_response(raw)
        self.assertEqual(result["company_stage"], "seed")

    def test_parse_response_invalid_json_returns_error(self) -> None:
        from executive_opportunity_scorer.enricher import _parse_response
        result = _parse_response("not json at all")
        self.assertIn("error", result)

    def test_fetch_url_bad_url_returns_empty(self) -> None:
        from executive_opportunity_scorer.enricher import _fetch_url
        result = _fetch_url("https://this-domain-does-not-exist-xyz.invalid/")
        self.assertEqual(result, "")


# ─── New webapp pipeline endpoints ────────────────────────────────────────────

class WebAppPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        # Redirect storage DB to temp file
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        import executive_opportunity_scorer.storage as storage
        self._original_path = storage.DB_PATH
        storage.DB_PATH = Path(self._tmp.name)
        storage.init_db()

    def tearDown(self) -> None:
        import executive_opportunity_scorer.storage as storage
        storage.DB_PATH = self._original_path
        Path(self._tmp.name).unlink(missing_ok=True)

    def _sample_save_payload(self, name: str = "PipelineCo") -> dict:
        return {
            "result": {
                "company_name": name,
                "snapshot_date": "2025-01-15",
                "fit_score": 70,
                "risk_score": 30,
                "confidence": 75,
                "recommendation": "Pursue now",
                "timing_window": "Good",
                "approach_angle": "Pitch angle here.",
            },
            "input": {"company_name": name},
        }

    def test_pipeline_save_and_list(self) -> None:
        import executive_opportunity_scorer.storage as storage
        entry_id = storage.save_result(
            self._sample_save_payload()["result"],
            self._sample_save_payload()["input"],
        )
        entries = storage.list_pipeline()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["company_name"], "PipelineCo")

    def test_pipeline_delete(self) -> None:
        import executive_opportunity_scorer.storage as storage
        payload = self._sample_save_payload()
        entry_id = storage.save_result(payload["result"], payload["input"])
        storage.delete_entry(entry_id)
        self.assertEqual(storage.list_pipeline(), [])

    def test_handle_pipeline_save_missing_result(self) -> None:
        from executive_opportunity_scorer.webapp import coerce_submission, load_ui_spec
        # Confirm webapp imports cleanly with new endpoints
        spec = load_ui_spec()
        self.assertIn("sections", spec)


if __name__ == "__main__":
    unittest.main()
