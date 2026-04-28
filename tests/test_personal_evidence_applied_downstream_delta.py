from __future__ import annotations

import csv
import json
import shutil
import unittest
from pathlib import Path

from src.personal_evidence_applied_downstream_delta import (
    HOLDING_FIELDS,
    run_personal_evidence_applied_downstream_delta,
)


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


class PersonalEvidenceAppliedDownstreamDeltaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_evidence_applied_delta"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.profiled = self.tmp / "profiled.csv"
        self.evidence_applied = self.tmp / "evidence_applied.csv"
        self.apply_summary = self.tmp / "apply_summary.csv"
        self.closure_summary = self.tmp / "closure_summary.csv"
        self.closure_holdings = self.tmp / "closure_holdings.csv"
        self.scores = self.tmp / "scores.csv"
        self.coverage = self.tmp / "coverage.csv"
        self.monthly = self.tmp / "monthly.csv"
        self.manifest = self.tmp / "manifest.json"
        self.used_inputs = self.tmp / "used_inputs.csv"
        self.summary_output = self.tmp / "summary.csv"
        self.holdings_output = self.tmp / "holdings.csv"
        self.report_output = self.tmp / "report.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_base_inputs(
        self,
        *,
        closure_rows: list[dict[str, str]] | None = None,
        coverage_rows: list[dict[str, str]] | None = None,
        score_rows: list[dict[str, str]] | None = None,
        monthly_rows: list[dict[str, str]] | None = None,
        evidence_row: dict[str, str] | None = None,
        source_mode: str = "EVIDENCE_APPLIED",
    ) -> None:
        master_fields = ["ticker", "isin", "company_name", "asset_type", "company_type_profile", "data_quality_flag", "revenue_cagr_5y", "roic"]
        write_csv(
            self.profiled,
            master_fields,
            [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "data_quality_flag": "MISSING_DATA", "revenue_cagr_5y": "", "roic": ""}],
        )
        write_csv(
            self.evidence_applied,
            master_fields,
            [
                evidence_row
                or {"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "data_quality_flag": "MISSING_DATA", "revenue_cagr_5y": "4.2", "roic": "12.0"}
            ],
        )
        write_csv(self.apply_summary, ["applied_rows_total"], [{"applied_rows_total": "2"}])
        write_csv(
            self.closure_summary,
            ["metric", "value", "notes"],
            [
                {"metric": "evidence_available_not_applied_total", "value": "1", "notes": ""},
                {"metric": "evidence_applied_but_still_missing_total", "value": "0", "notes": ""},
                {"metric": "missing_required_kpi_total", "value": "1", "notes": ""},
            ],
        )
        write_csv(
            self.closure_holdings,
            [
                "ticker",
                "isin",
                "company_name",
                "asset_type",
                "company_type_profile",
                "data_quality_flag",
                "likely_blocker",
                "missing_required_kpis",
            ],
            closure_rows
            or [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "company_name": "Alpha",
                    "asset_type": "STOCK",
                    "company_type_profile": "STANDARD",
                    "data_quality_flag": "MISSING_DATA",
                    "likely_blocker": "EVIDENCE_AVAILABLE_NOT_APPLIED",
                    "missing_required_kpis": "revenue_cagr_5y; roic",
                }
            ],
        )
        write_csv(
            self.coverage,
            ["ticker", "isin", "holding_name", "asset_type", "company_type_profile", "missing_required_kpis"],
            coverage_rows
            if coverage_rows is not None
            else [{"ticker": "AAA", "isin": "US1", "holding_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "missing_required_kpis": ""}],
        )
        write_csv(
            self.scores,
            ["ticker", "isin", "data_quality_flag"],
            score_rows if score_rows is not None else [{"ticker": "AAA", "isin": "US1", "data_quality_flag": "OK"}],
        )
        write_csv(
            self.monthly,
            ["rank", "ticker", "target_action"],
            monthly_rows if monthly_rows is not None else [{"rank": "1", "ticker": "AAA", "target_action": "BUY_CANDIDATE"}],
        )
        self.manifest.write_text(
            json.dumps({"inputs": {"use_evidence_applied_master": source_mode == "EVIDENCE_APPLIED", "use_profiled_master": source_mode == "PROFILED"}}),
            encoding="utf-8",
        )
        write_csv(
            self.used_inputs,
            ["stage_name", "stage_status", "input_role", "input_path", "input_exists", "notes"],
            [
                {
                    "stage_name": "scoring",
                    "stage_status": "SUCCESS",
                    "input_role": "fundamentals_master",
                    "input_path": "data/processed/personal_fundamentals_master_evidence_applied.csv",
                    "input_exists": "True",
                    "notes": f"fundamentals_source_mode={source_mode}",
                }
            ],
        )

    def run_report(self):
        return run_personal_evidence_applied_downstream_delta(
            profiled_master_input=str(self.profiled),
            evidence_applied_master_input=str(self.evidence_applied),
            evidence_apply_summary_input=str(self.apply_summary),
            closure_summary_input=str(self.closure_summary),
            closure_holdings_input=str(self.closure_holdings),
            scores_input=str(self.scores),
            coverage_input=str(self.coverage),
            monthly_input=str(self.monthly),
            run_manifest_input=str(self.manifest),
            run_used_inputs_input=str(self.used_inputs),
            summary_output=str(self.summary_output),
            holdings_output=str(self.holdings_output),
            report_output=str(self.report_output),
        )

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary_output)}[metric]

    def test_evidence_applied_source_mode_is_detected(self) -> None:
        self.write_base_inputs()
        result = self.run_report()

        self.assertEqual(result.master_usage.source_mode, "EVIDENCE_APPLIED")
        self.assertEqual(self.summary_value("use_evidence_applied_master"), "True")

    def test_previous_evidence_available_now_applied_is_resolved(self) -> None:
        self.write_base_inputs(score_rows=[{"ticker": "AAA", "isin": "US1", "data_quality_flag": "MISSING_DATA"}])
        self.run_report()

        holding = read_csv(self.holdings_output)[0]
        self.assertEqual(holding["current_likely_blocker"], "evidence_available_not_applied_resolved")
        self.assertIn("revenue_cagr_5y", holding["newly_available_kpis"])

    def test_still_missing_after_evidence_is_separate(self) -> None:
        self.write_base_inputs(
            coverage_rows=[{"ticker": "AAA", "isin": "US1", "holding_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "missing_required_kpis": "roic"}],
            evidence_row={"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "data_quality_flag": "MISSING_DATA", "revenue_cagr_5y": "4.2", "roic": ""},
            score_rows=[{"ticker": "AAA", "isin": "US1", "data_quality_flag": "MISSING_DATA"}],
        )
        self.run_report()

        holding = read_csv(self.holdings_output)[0]
        self.assertEqual(holding["current_likely_blocker"], "still_missing_after_evidence")
        self.assertEqual(holding["current_missing_required_kpis"], "roic")

    def test_financial_other_etf_non_us_are_separate(self) -> None:
        self.write_base_inputs(
            closure_rows=[
                {"ticker": "FIN", "isin": "USF", "company_name": "Financial", "asset_type": "STOCK", "company_type_profile": "FINANCIAL", "data_quality_flag": "MISSING_DATA", "likely_blocker": "FINANCIAL_PROFILE", "missing_required_kpis": ""},
                {"ticker": "OTH", "isin": "USO", "company_name": "Other", "asset_type": "STOCK", "company_type_profile": "OTHER", "data_quality_flag": "MISSING_DATA", "likely_blocker": "OTHER_PROFILE", "missing_required_kpis": ""},
                {"ticker": "ETF", "isin": "IE1", "company_name": "ETF", "asset_type": "ETF", "company_type_profile": "OTHER", "data_quality_flag": "MISSING_DATA", "likely_blocker": "ETF_OR_ADR_OR_NON_COMPANY", "missing_required_kpis": ""},
                {"ticker": "NON", "isin": "NL1", "company_name": "Non US", "asset_type": "STOCK", "company_type_profile": "OTHER", "data_quality_flag": "MISSING_DATA", "likely_blocker": "NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE", "missing_required_kpis": ""},
            ],
            coverage_rows=[
                {"ticker": "FIN", "isin": "USF", "holding_name": "Financial", "asset_type": "STOCK", "company_type_profile": "FINANCIAL", "missing_required_kpis": ""},
                {"ticker": "OTH", "isin": "USO", "holding_name": "Other", "asset_type": "STOCK", "company_type_profile": "OTHER", "missing_required_kpis": ""},
                {"ticker": "ETF", "isin": "IE1", "holding_name": "ETF", "asset_type": "ETF", "company_type_profile": "OTHER", "missing_required_kpis": ""},
                {"ticker": "NON", "isin": "NL1", "holding_name": "Non US", "asset_type": "STOCK", "company_type_profile": "OTHER", "missing_required_kpis": ""},
            ],
            score_rows=[
                {"ticker": "FIN", "isin": "USF", "data_quality_flag": "MISSING_DATA"},
                {"ticker": "OTH", "isin": "USO", "data_quality_flag": "MISSING_DATA"},
                {"ticker": "ETF", "isin": "IE1", "data_quality_flag": "MISSING_DATA"},
                {"ticker": "NON", "isin": "NL1", "data_quality_flag": "MISSING_DATA"},
            ],
        )
        self.run_report()

        blockers = {row["current_likely_blocker"] for row in read_csv(self.holdings_output)}
        self.assertEqual(blockers, {"still_blocked_financial", "still_blocked_other", "still_blocked_etf_or_adr", "still_blocked_non_us"})

    def test_missing_optional_inputs_warn_without_crash(self) -> None:
        write_csv(
            self.closure_holdings,
            ["ticker", "isin", "company_name", "asset_type", "company_type_profile", "data_quality_flag", "likely_blocker", "missing_required_kpis"],
            [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "data_quality_flag": "MISSING_DATA", "likely_blocker": "EVIDENCE_AVAILABLE_NOT_APPLIED", "missing_required_kpis": "roic"}],
        )

        result = self.run_report()

        self.assertTrue(result.warnings)
        self.assertTrue(self.summary_output.exists())
        self.assertTrue(self.holdings_output.exists())
        self.assertEqual(self.summary_value("warnings_total"), str(len(result.warnings)))

    def test_sorting_is_deterministic(self) -> None:
        self.write_base_inputs(
            closure_rows=[
                {"ticker": "ZZZ", "isin": "US3", "company_name": "Zeta", "asset_type": "STOCK", "company_type_profile": "STANDARD", "data_quality_flag": "MISSING_DATA", "likely_blocker": "EVIDENCE_AVAILABLE_NOT_APPLIED", "missing_required_kpis": "roic"},
                {"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "ETF", "company_type_profile": "OTHER", "data_quality_flag": "MISSING_DATA", "likely_blocker": "ETF_OR_ADR_OR_NON_COMPANY", "missing_required_kpis": ""},
            ],
            coverage_rows=[
                {"ticker": "ZZZ", "isin": "US3", "holding_name": "Zeta", "asset_type": "STOCK", "company_type_profile": "STANDARD", "missing_required_kpis": "roic"},
                {"ticker": "AAA", "isin": "US1", "holding_name": "Alpha", "asset_type": "ETF", "company_type_profile": "OTHER", "missing_required_kpis": ""},
            ],
        )
        self.run_report()

        rows = read_csv(self.holdings_output)
        self.assertEqual(list(rows[0].keys()), HOLDING_FIELDS)
        self.assertEqual([row["ticker"] for row in rows], ["AAA", "ZZZ"])

    def test_report_masks_private_paths_from_warnings(self) -> None:
        self.write_base_inputs()
        result = run_personal_evidence_applied_downstream_delta(
            profiled_master_input="data/raw/private/secret/profiled.csv",
            evidence_applied_master_input=str(self.evidence_applied),
            evidence_apply_summary_input=str(self.apply_summary),
            closure_summary_input=str(self.closure_summary),
            closure_holdings_input=str(self.closure_holdings),
            scores_input=str(self.scores),
            coverage_input=str(self.coverage),
            monthly_input=str(self.monthly),
            run_manifest_input=str(self.manifest),
            run_used_inputs_input=str(self.used_inputs),
            summary_output=str(self.summary_output),
            holdings_output=str(self.holdings_output),
            report_output=str(self.report_output),
        )

        report = self.report_output.read_text(encoding="utf-8")
        self.assertTrue(result.warnings)
        self.assertIn("<private_path>", report)
        self.assertNotIn("data/raw/private", report.replace("\\", "/"))
        self.assertNotIn("secret", report)


if __name__ == "__main__":
    unittest.main()
