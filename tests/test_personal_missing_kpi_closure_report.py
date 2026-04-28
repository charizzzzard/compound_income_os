from __future__ import annotations

import csv
import json
import shutil
import unittest
from pathlib import Path

from src.personal_missing_kpi_closure_report import (
    HOLDING_FIELDS,
    SUMMARY_FIELDS,
    run_personal_missing_kpi_closure_report,
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


class PersonalMissingKpiClosureReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_missing_kpi_closure"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.profiled = self.tmp / "profiled.csv"
        self.evidence_applied = self.tmp / "evidence_applied.csv"
        self.overlay_applied = self.tmp / "overlay_applied.csv"
        self.coverage = self.tmp / "coverage.csv"
        self.scores = self.tmp / "scores.csv"
        self.gap = self.tmp / "gap.csv"
        self.gap_summary = self.tmp / "gap_summary.csv"
        self.evidence_registry = self.tmp / "evidence_registry.csv"
        self.apply_summary = self.tmp / "apply_summary.csv"
        self.snapshot_summary = self.tmp / "snapshot_summary.csv"
        self.unlock = self.tmp / "unlock.csv"
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
        gap_rows: list[dict[str, str]] | None = None,
        evidence_rows: list[dict[str, str]] | None = None,
        evidence_applied_rows: list[dict[str, str]] | None = None,
        source_mode: str = "PROFILED",
        use_evidence_applied: bool = False,
    ) -> None:
        master_fields = ["ticker", "isin", "company_name", "asset_type", "company_type_profile", "data_quality_flag", "revenue_cagr_5y", "roic", "eps_cagr_5y"]
        write_csv(
            self.profiled,
            master_fields,
            [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "data_quality_flag": "MISSING_DATA", "revenue_cagr_5y": "", "roic": "", "eps_cagr_5y": ""}],
        )
        write_csv(
            self.evidence_applied,
            master_fields,
            evidence_applied_rows
            if evidence_applied_rows is not None
            else [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "data_quality_flag": "MISSING_DATA", "revenue_cagr_5y": "", "roic": "", "eps_cagr_5y": ""}],
        )
        write_csv(self.overlay_applied, master_fields, [])
        write_csv(
            self.coverage,
            ["ticker", "isin", "holding_name", "asset_type", "company_type_profile", "missing_required_kpis"],
            [{"ticker": "AAA", "isin": "US1", "holding_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "missing_required_kpis": "revenue_cagr_5y; roic"}],
        )
        write_csv(self.scores, ["ticker", "isin", "data_quality_flag"], [{"ticker": "AAA", "isin": "US1", "data_quality_flag": "MISSING_DATA"}])
        write_csv(
            self.gap,
            [
                "ticker",
                "isin",
                "company_name",
                "asset_type",
                "company_type_profile",
                "current_data_quality_flag",
                "missing_required_kpis_under_current_profile",
                "quality_gap_type",
            ],
            gap_rows
            or [
                {
                    "ticker": "AAA",
                    "isin": "US1",
                    "company_name": "Alpha",
                    "asset_type": "STOCK",
                    "company_type_profile": "STANDARD",
                    "current_data_quality_flag": "MISSING_DATA",
                    "missing_required_kpis_under_current_profile": "revenue_cagr_5y; roic",
                    "quality_gap_type": "SEC_KPI_MISSING",
                }
            ],
        )
        write_csv(self.gap_summary, ["summary_metric", "summary_value"], [{"summary_metric": "rows_total", "summary_value": "1"}])
        write_csv(
            self.evidence_registry,
            ["ticker", "isin", "kpi_name", "evidence_present", "reported_value"],
            evidence_rows or [],
        )
        write_csv(self.apply_summary, ["applied_rows_total"], [{"applied_rows_total": "0"}])
        write_csv(self.snapshot_summary, ["snapshot_rows_total"], [{"snapshot_rows_total": "0"}])
        write_csv(
            self.unlock,
            ["ticker", "isin", "company_name", "asset_type", "company_type_profile", "data_quality_flag", "quality_gap_type"],
            [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "data_quality_flag": "MISSING_DATA", "quality_gap_type": "SEC_KPI_MISSING"}],
        )
        self.manifest.write_text(
            json.dumps({"inputs": {"use_profiled_master": source_mode == "PROFILED", "use_evidence_applied_master": use_evidence_applied}}),
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
                    "input_path": "data/processed/personal_fundamentals_master_profiled.csv",
                    "input_exists": "True",
                    "notes": f"fundamentals_source_mode={source_mode}; no sample fallback",
                }
            ],
        )

    def run_report(self):
        return run_personal_missing_kpi_closure_report(
            profiled_master_input=str(self.profiled),
            evidence_applied_master_input=str(self.evidence_applied),
            overlay_applied_master_input=str(self.overlay_applied),
            coverage_input=str(self.coverage),
            scores_input=str(self.scores),
            gap_diagnostics_input=str(self.gap),
            gap_summary_input=str(self.gap_summary),
            evidence_registry_input=str(self.evidence_registry),
            evidence_apply_summary_input=str(self.apply_summary),
            snapshot_summary_input=str(self.snapshot_summary),
            unlock_holdings_input=str(self.unlock),
            run_manifest_input=str(self.manifest),
            run_used_inputs=str(self.used_inputs),
            summary_output=str(self.summary_output),
            holdings_output=str(self.holdings_output),
            report_output=str(self.report_output),
        )

    def summary_value(self, metric: str) -> str:
        return {row["metric"]: row["value"] for row in read_csv(self.summary_output)}[metric]

    def test_standard_missing_kpi_gets_sec_or_manual_action(self) -> None:
        self.write_base_inputs()
        self.run_report()

        holding = read_csv(self.holdings_output)[0]
        self.assertEqual(holding["likely_blocker"], "SEC_KPI_MISSING")
        self.assertEqual(self.summary_value("missing_required_kpi_total"), "1")
        self.assertIn("SEC snapshot", holding["recommended_next_action"])

    def test_evidence_registry_hit_without_current_applied_master_is_not_applied(self) -> None:
        self.write_base_inputs(
            gap_rows=[
                {"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "revenue_cagr_5y; roic", "quality_gap_type": "SEC_KPI_PARTIAL"}
            ],
            evidence_rows=[{"ticker": "AAA", "isin": "US1", "kpi_name": "revenue_cagr_5y", "evidence_present": "True", "reported_value": "4.2"}],
        )
        self.run_report()

        holding = read_csv(self.holdings_output)[0]
        self.assertEqual(holding["likely_blocker"], "EVIDENCE_AVAILABLE_NOT_APPLIED")
        self.assertEqual(self.summary_value("evidence_available_not_applied_total"), "1")
        self.assertEqual(self.summary_value("profiled_vs_evidence_applied_master_finding"), "LIKELY_PROFILED_MASTER_INSTEAD_OF_EVIDENCE_APPLIED_FOR_EVIDENCE_ROWS")

    def test_evidence_applied_but_still_missing_is_classified_separately(self) -> None:
        self.write_base_inputs(
            gap_rows=[
                {"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "revenue_cagr_5y; roic", "quality_gap_type": "SEC_KPI_PARTIAL"}
            ],
            evidence_rows=[{"ticker": "AAA", "isin": "US1", "kpi_name": "revenue_cagr_5y", "evidence_present": "True", "reported_value": "4.2"}],
            evidence_applied_rows=[{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "data_quality_flag": "MISSING_DATA", "revenue_cagr_5y": "4.2", "roic": "", "eps_cagr_5y": ""}],
            source_mode="EVIDENCE_APPLIED",
            use_evidence_applied=True,
        )
        self.run_report()

        holding = read_csv(self.holdings_output)[0]
        self.assertEqual(holding["likely_blocker"], "EVIDENCE_APPLIED_BUT_STILL_MISSING")
        self.assertEqual(holding["evidence_applied_flag"], "True")
        self.assertEqual(self.summary_value("evidence_applied_but_still_missing_total"), "1")

    def test_financial_and_other_are_not_counted_as_standard_kpi_errors(self) -> None:
        self.write_base_inputs(
            gap_rows=[
                {"ticker": "FIN", "isin": "USF", "company_name": "Financial", "asset_type": "STOCK", "company_type_profile": "FINANCIAL", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "", "quality_gap_type": "COVERED"},
                {"ticker": "OTH", "isin": "USO", "company_name": "Other", "asset_type": "STOCK", "company_type_profile": "OTHER", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "", "quality_gap_type": "COVERED"},
            ]
        )
        self.run_report()

        self.assertEqual(self.summary_value("financial_profile_total"), "1")
        self.assertEqual(self.summary_value("other_profile_total"), "1")
        self.assertEqual(self.summary_value("missing_required_kpi_total"), "0")

    def test_non_us_is_counted_separately(self) -> None:
        self.write_base_inputs(
            gap_rows=[
                {"ticker": "NON", "isin": "NL1", "company_name": "Non US", "asset_type": "STOCK", "company_type_profile": "OTHER", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "", "quality_gap_type": "NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE"}
            ]
        )
        self.run_report()

        self.assertEqual(self.summary_value("non_us_total"), "1")
        self.assertEqual(read_csv(self.holdings_output)[0]["likely_blocker"], "NON_US_OR_UNSUPPORTED_BY_CURRENT_SEC_SCOPE")

    def test_etf_and_adr_are_counted_separately(self) -> None:
        self.write_base_inputs(
            gap_rows=[
                {"ticker": "ETF", "isin": "IE1", "company_name": "ETF", "asset_type": "ETF", "company_type_profile": "OTHER", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "", "quality_gap_type": "ETF_OR_NON_COMPANY_FUNDAMENTALS"},
                {"ticker": "ADR", "isin": "US2", "company_name": "ADR", "asset_type": "ADR", "company_type_profile": "OTHER", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "", "quality_gap_type": "ETF_OR_NON_COMPANY_FUNDAMENTALS"},
            ]
        )
        self.run_report()

        self.assertEqual(self.summary_value("etf_or_adr_total"), "2")
        self.assertEqual({row["likely_blocker"] for row in read_csv(self.holdings_output)}, {"ETF_OR_ADR_OR_NON_COMPANY"})

    def test_missing_optional_inputs_warn_without_crash(self) -> None:
        write_csv(
            self.gap,
            ["ticker", "isin", "company_name", "asset_type", "company_type_profile", "current_data_quality_flag", "missing_required_kpis_under_current_profile", "quality_gap_type"],
            [{"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "STOCK", "company_type_profile": "STANDARD", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "roic", "quality_gap_type": "SEC_KPI_MISSING"}],
        )

        result = self.run_report()

        self.assertTrue(result.warnings)
        self.assertTrue(self.summary_output.exists())
        self.assertTrue(self.holdings_output.exists())
        self.assertEqual(self.summary_value("warnings_total"), str(len(result.warnings)))

    def test_report_sorting_and_fields_are_deterministic(self) -> None:
        self.write_base_inputs(
            gap_rows=[
                {"ticker": "ZZZ", "isin": "US3", "company_name": "Zeta", "asset_type": "STOCK", "company_type_profile": "STANDARD", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "roic", "quality_gap_type": "SEC_KPI_MISSING"},
                {"ticker": "AAA", "isin": "US1", "company_name": "Alpha", "asset_type": "ETF", "company_type_profile": "OTHER", "current_data_quality_flag": "MISSING_DATA", "missing_required_kpis_under_current_profile": "", "quality_gap_type": "ETF_OR_NON_COMPANY_FUNDAMENTALS"},
            ]
        )
        self.run_report()

        rows = read_csv(self.holdings_output)
        self.assertEqual(list(rows[0].keys()), HOLDING_FIELDS)
        self.assertEqual([row["ticker"] for row in rows], ["AAA", "ZZZ"])
        self.assertEqual(list(read_csv(self.summary_output)[0].keys()), SUMMARY_FIELDS)


if __name__ == "__main__":
    unittest.main()
