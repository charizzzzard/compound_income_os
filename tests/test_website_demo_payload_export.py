from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

from src.website_demo_payload_export import run_website_demo_payload_export


class WebsiteDemoPayloadExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_website_demo_payload_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.source = self.tmp / "dashboard_readiness_payload.json"
        self.sample = self.tmp / "public" / "demo" / "readiness_payload.sample.json"
        self.readme = self.tmp / "public" / "demo" / "README.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_payload(self, overrides: dict | None = None) -> None:
        payload = {
            "metadata": {
                "generated_at": "2026-04-27",
                "source_artifacts": ["data/processed/dashboard_readiness_payload.json"],
                "schema_version": "1",
                "private_data_included": False,
                "dummy_claims_included": False,
            },
            "readiness": {
                "demo": {"status": "BLOCKED", "reason_codes": ["WATCHLIST_SAMPLE_INPUT"]},
                "decision": {"status": "BLOCKED", "reason_codes": ["MISSING_VALUATION_REQUIRED"]},
                "dashboard": {"status": "REVIEW", "reason_codes": []},
                "handoff": {"status": "REVIEW", "reason_codes": []},
            },
            "summary": {"active_blockers_count": 11, "p0_blockers_count": 6, "p1_review_count": 4, "resolved_blockers_count": 2, "next_actions_count": 5},
            "sections": {
                "next_actions": [
                    {
                        "id": "valuation",
                        "label": "Review private valuation inputs",
                        "value": "P0_BLOCKER",
                        "status": "REVIEW",
                        "severity": "P0_BLOCKER",
                        "description": "Review workflow input.",
                        "source_artifact": "data/processed/personal_valuation_input_contract_summary.csv",
                        "reason_codes": ["MISSING_VALUATION_REQUIRED"],
                        "cta_label": "Review private valuation inputs",
                        "cta_target": "data/processed/personal_valuation_input_contract_summary.csv",
                        "is_safe_action": True,
                    }
                ]
            },
            "guardrails": {"no_advice_language": True, "no_private_values": True, "no_network": True, "no_score_mutation": True, "no_master_mutation": True},
        }
        if overrides:
            payload.update(overrides)
        self.source.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def test_valid_payload_exports_sample_with_metadata(self) -> None:
        self.write_payload()

        result = run_website_demo_payload_export(
            source_payload=str(self.source),
            sample_output=str(self.sample),
            readme_output=str(self.readme),
        )
        sample = json.loads(self.sample.read_text(encoding="utf-8"))

        self.assertTrue(result.sample_output.exists())
        self.assertEqual(sample["sample_metadata"]["sample_type"], "private_preview_readiness_payload")
        self.assertFalse(sample["sample_metadata"]["public_deploy_ready"])
        self.assertFalse(sample["sample_metadata"]["contains_private_data"])
        self.assertFalse(sample["sample_metadata"]["contains_investment_advice"])
        self.assertEqual(sample["payload"]["readiness"]["decision"]["status"], "BLOCKED")
        self.assertEqual(sample["website_mockup_wave_two"]["evidence_page"]["route"], "/evidence")
        self.assertEqual(sample["website_mockup_wave_two"]["evidence_page"]["product_mockup"], "P3 Evidence Workspace")
        self.assertFalse(sample["website_mockup_wave_two"]["evidence_workspace"]["network_performed"])
        self.assertIn("Evidence Apply", sample["website_mockup_wave_two"]["sec_pipeline_stages"])

    def test_private_raw_path_is_blocked(self) -> None:
        self.write_payload({"metadata": {"private_data_included": False, "dummy_claims_included": False, "source_artifacts": ["data/raw/private/secret.csv"]}})

        with self.assertRaisesRegex(ValueError, "private marker"):
            run_website_demo_payload_export(
                source_payload=str(self.source),
                sample_output=str(self.sample),
                readme_output=str(self.readme),
            )

    def test_forbidden_action_word_is_blocked(self) -> None:
        self.write_payload()
        payload = json.loads(self.source.read_text(encoding="utf-8"))
        payload["sections"]["next_actions"][0]["cta_label"] = "Buy"
        self.source.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "market-action"):
            run_website_demo_payload_export(
                source_payload=str(self.source),
                sample_output=str(self.sample),
                readme_output=str(self.readme),
            )

    def test_decision_pass_is_not_exported_for_private_preview(self) -> None:
        self.write_payload()
        payload = json.loads(self.source.read_text(encoding="utf-8"))
        payload["readiness"]["decision"]["status"] = "PASS"
        self.source.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "decision readiness PASS"):
            run_website_demo_payload_export(
                source_payload=str(self.source),
                sample_output=str(self.sample),
                readme_output=str(self.readme),
            )


if __name__ == "__main__":
    unittest.main()
