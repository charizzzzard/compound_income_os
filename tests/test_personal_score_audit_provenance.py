from __future__ import annotations

import csv
import json
import shutil
import unittest
from pathlib import Path

from src.personal_score_audit_provenance import run_personal_score_audit_provenance


ROOT = Path(__file__).resolve().parent.parent


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class PersonalScoreAuditProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_score_audit_provenance"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.score_audit = self.tmp / "score_audit.csv"
        self.profiled = self.tmp / "profiled.csv"
        self.applied = self.tmp / "applied.csv"
        self.registry = self.tmp / "registry.csv"
        self.raw_master = self.tmp / "raw_master.csv"
        self.overlay = self.tmp / "overlay.csv"
        self.metrics = self.tmp / "metrics.json"
        self.used_inputs = self.tmp / "used_inputs.csv"
        self.manifest = self.tmp / "manifest.json"
        self.provenance_output = self.tmp / "provenance.csv"
        self.summary_output = self.tmp / "summary.csv"
        self.report_output = self.tmp / "report.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_base_inputs(
        self,
        *,
        registry_rows: list[dict[str, str]] | None = None,
        applied_value: str = "12.3",
        score_value: str = "12.3",
        profile: str = "STANDARD",
    ) -> None:
        write_csv(
            self.score_audit,
            ["ticker", "isin", "company_name", "company_type_profile", "revenue_cagr_5y"],
            [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "company_type_profile": profile, "revenue_cagr_5y": score_value}],
        )
        master_fields = ["ticker", "isin", "company_name", "company_type_profile", "source_name", "source_as_of_date", "revenue_cagr_5y"]
        write_csv(self.profiled, master_fields, [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "company_type_profile": profile, "source_name": "profiled", "source_as_of_date": "2026-01-01", "revenue_cagr_5y": ""}])
        write_csv(self.applied, master_fields, [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "company_type_profile": profile, "source_name": "evidence applied", "source_as_of_date": "2026-01-02", "revenue_cagr_5y": applied_value}])
        write_csv(self.raw_master, master_fields, [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "company_type_profile": profile, "source_name": "raw", "source_as_of_date": "2025-12-31", "revenue_cagr_5y": ""}])
        write_csv(
            self.registry,
            ["ticker", "isin", "company_name", "company_type_profile", "kpi_name", "source_type", "source_name", "source_reference", "source_as_of_date", "verification_status", "data_quality_flag", "evidence_present", "reported_value"],
            registry_rows
            if registry_rows is not None
            else [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "company_name": "Alpha",
                    "company_type_profile": profile,
                    "kpi_name": "revenue_cagr_5y",
                    "source_type": "SEC",
                    "source_name": "CompanyFacts",
                    "source_reference": "CIK0000000001",
                    "source_as_of_date": "2026-01-02",
                    "verification_status": "REVIEWED",
                    "data_quality_flag": "OK",
                    "evidence_present": "True",
                    "reported_value": "12.3",
                }
            ],
        )
        write_csv(self.overlay, ["ticker", "isin", "company_name", "source_reference"], [])
        self.metrics.write_text(
            json.dumps({"kpis": {"revenue_cagr_5y": {"kpi_tier": "CORE_QUALITY_REQUIRED", "coverage_required": True}}}),
            encoding="utf-8",
        )
        write_csv(self.used_inputs, ["stage_name", "input_role", "input_path", "notes"], [])
        self.manifest.write_text(json.dumps({}), encoding="utf-8")

    def run_report(self, **overrides):
        args = {
            "score_audit_input": str(self.score_audit),
            "profiled_master_input": str(self.profiled),
            "evidence_applied_master_input": str(self.applied),
            "evidence_registry_input": str(self.registry),
            "raw_master_input": str(self.raw_master),
            "overlay_input": str(self.overlay),
            "metric_definitions_input": str(self.metrics),
            "run_used_inputs_input": str(self.used_inputs),
            "run_manifest_input": str(self.manifest),
            "provenance_output": str(self.provenance_output),
            "summary_output": str(self.summary_output),
            "report_output": str(self.report_output),
        }
        args.update(overrides)
        return run_personal_score_audit_provenance(**args)

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary_output)}[metric]

    def test_exact_isin_and_kpi_match_with_source_reference_is_trusted(self) -> None:
        self.write_base_inputs()
        self.run_report()

        row = read_csv(self.provenance_output)[0]
        self.assertEqual(row["provenance_status"], "TRUSTED")
        self.assertEqual(row["reason_code"], "SOURCE_MATCHED")
        self.assertEqual(row["source_layer"], "EVIDENCE_REGISTRY")
        self.assertEqual(row["score_audit_value"], "12.3")
        self.assertEqual(self.summary_value("provenance_status__TRUSTED"), "1")

    def test_value_present_without_source_reference_or_date_is_partial(self) -> None:
        self.write_base_inputs(
            registry_rows=[
                {"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "company_type_profile": "STANDARD", "kpi_name": "revenue_cagr_5y", "source_type": "SEC", "source_name": "CompanyFacts", "source_reference": "", "source_as_of_date": "", "verification_status": "REVIEWED", "data_quality_flag": "OK", "evidence_present": "True", "reported_value": "12.3"}
            ]
        )
        self.run_report()

        row = read_csv(self.provenance_output)[0]
        self.assertEqual(row["provenance_status"], "PARTIAL")
        self.assertEqual(row["reason_code"], "VALUE_PRESENT_NO_SOURCE_REFERENCE")

    def test_score_audit_value_without_evidence_or_applied_match_is_partial(self) -> None:
        self.write_base_inputs(registry_rows=[], applied_value="", score_value="12.3")
        self.run_report()

        row = read_csv(self.provenance_output)[0]
        self.assertEqual(row["source_layer"], "SCORE_AUDIT_ONLY")
        self.assertEqual(row["provenance_status"], "PARTIAL")
        self.assertEqual(row["reason_code"], "EVIDENCE_REGISTRY_MISSING")

    def test_multiple_sources_are_ambiguous_without_silent_selection(self) -> None:
        self.write_base_inputs(
            registry_rows=[
                {"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "company_type_profile": "STANDARD", "kpi_name": "revenue_cagr_5y", "source_type": "SEC", "source_name": "CompanyFacts", "source_reference": "ref1", "source_as_of_date": "2026-01-02", "verification_status": "REVIEWED", "data_quality_flag": "OK", "evidence_present": "True", "reported_value": "12.3"},
                {"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "company_type_profile": "STANDARD", "kpi_name": "revenue_cagr_5y", "source_type": "Manual", "source_name": "Review", "source_reference": "ref2", "source_as_of_date": "2026-01-03", "verification_status": "REVIEWED", "data_quality_flag": "OK", "evidence_present": "True", "reported_value": "12.3"},
            ]
        )
        self.run_report()

        row = read_csv(self.provenance_output)[0]
        self.assertEqual(row["provenance_status"], "AMBIGUOUS")
        self.assertEqual(row["source_layer"], "AMBIGUOUS")
        self.assertEqual(row["reason_code"], "MULTIPLE_SOURCE_CANDIDATES")

    def test_non_standard_profile_is_not_applicable(self) -> None:
        self.write_base_inputs(profile="FINANCIAL")
        self.run_report()

        row = read_csv(self.provenance_output)[0]
        self.assertEqual(row["provenance_status"], "NOT_APPLICABLE")
        self.assertEqual(row["source_layer"], "NOT_APPLICABLE")
        self.assertEqual(row["reason_code"], "PROFILE_NOT_STANDARD")

    def test_missing_input_artifacts_create_empty_outputs_without_crash(self) -> None:
        self.metrics.write_text(json.dumps({"kpis": {"revenue_cagr_5y": {"kpi_tier": "CORE_QUALITY_REQUIRED"}}}), encoding="utf-8")
        self.run_report(
            score_audit_input=str(self.tmp / "missing_score_audit.csv"),
            profiled_master_input=str(self.tmp / "missing_profiled.csv"),
            evidence_applied_master_input=str(self.tmp / "missing_applied.csv"),
            evidence_registry_input=str(self.tmp / "missing_registry.csv"),
            raw_master_input=str(self.tmp / "missing_raw.csv"),
            overlay_input=str(self.tmp / "missing_overlay.csv"),
            run_used_inputs_input=str(self.tmp / "missing_used.csv"),
            run_manifest_input=str(self.tmp / "missing_manifest.json"),
        )

        self.assertEqual(read_csv(self.provenance_output), [])
        self.assertEqual(self.summary_value("provenance_rows_total"), "0")
        self.assertNotEqual(self.summary_value("warnings_total"), "0")

    def test_private_paths_are_sanitized_in_report(self) -> None:
        self.write_base_inputs()
        self.run_report(raw_master_input="data/raw/private/fundamentals/private_master.csv")

        report = self.report_output.read_text(encoding="utf-8")
        self.assertIn("<private_path>", report)
        self.assertNotIn("data/raw/private/fundamentals/private_master.csv", report)


if __name__ == "__main__":
    unittest.main()
