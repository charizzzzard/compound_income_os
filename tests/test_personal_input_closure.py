from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from src.personal_input_closure import FIELDNAMES, run_personal_input_closure

ROOT = Path(__file__).resolve().parent.parent


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, metrics: dict[str, str]) -> None:
    rows = [{"metric": key, "value": value, "notes": ""} for key, value in sorted(metrics.items())]
    write_csv(path, ["metric", "value", "notes"], rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class PersonalInputClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_personal_input_closure"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.watchlist = self.tmp / "watchlist_summary.csv"
        self.valuation = self.tmp / "valuation_summary.csv"
        self.dividend = self.tmp / "dividend_summary.csv"
        self.provenance = self.tmp / "provenance_summary.csv"
        self.core = self.tmp / "core_summary.csv"
        self.output = self.tmp / "personal_input_closure_report.csv"
        self.report = self.tmp / "personal_input_closure_report.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def run_closure(self, **overrides):
        params = {
            "as_of_date": "2026-05-18",
            "output": str(self.output),
            "report": str(self.report),
            "watchlist_summary": str(self.watchlist),
            "valuation_summary": str(self.valuation),
            "dividend_fcf_summary": str(self.dividend),
            "kpi_provenance_summary": str(self.provenance),
            "core_kpi_summary": str(self.core),
        }
        params.update(overrides)
        return run_personal_input_closure(**params)

    def rows_by_area(self) -> dict[str, dict[str, str]]:
        return {row["input_area"]: row for row in read_csv(self.output)}

    def write_ready_supporting_summaries(self) -> None:
        write_summary(
            self.valuation,
            {
                "affected_standard_rows_count": "0",
                "approved_rows_count": "0",
                "input_file_status": "PRESENT",
                "invalid_rows_count": "0",
                "missing_rows_count": "0",
                "reason_codes": "PROFILE_NOT_STANDARD",
                "review_rows_count": "0",
            },
        )
        write_summary(
            self.dividend,
            {
                "affected_standard_rows_count": "0",
                "approved_rows_count": "0",
                "input_file_status": "PRESENT",
                "invalid_rows_count": "0",
                "missing_rows_count": "0",
                "reason_codes": "PROFILE_NOT_STANDARD",
                "review_rows_count": "0",
                "sec_evidence_possible_count": "0",
            },
        )
        write_summary(
            self.provenance,
            {
                "holdings_with_incomplete_provenance_total": "0",
                "provenance_incomplete_flag": "False",
                "provenance_status__AMBIGUOUS": "0",
                "provenance_status__MISSING": "0",
                "provenance_status__PARTIAL": "0",
                "provenance_status__TRUSTED": "4",
            },
        )

    def test_cli_help_works(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "src.personal_input_closure", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("--as-of-date", completed.stdout)
        self.assertIn("--watchlist-summary", completed.stdout)

    def test_missing_input_artifacts_are_visible_for_required_areas(self) -> None:
        self.run_closure(
            watchlist_summary=str(self.tmp / "missing_watchlist.csv"),
            valuation_summary=str(self.tmp / "missing_valuation.csv"),
            dividend_fcf_summary=str(self.tmp / "missing_dividend.csv"),
            kpi_provenance_summary=str(self.tmp / "missing_provenance.csv"),
            core_kpi_summary=str(self.tmp / "missing_core.csv"),
        )

        rows = self.rows_by_area()
        self.assertEqual(set(rows), {"WATCHLIST", "VALUATION", "DIVIDEND_FCF", "KPI_PROVENANCE"})
        for area in rows:
            self.assertEqual(rows[area]["status"], "MISSING")
            self.assertEqual(rows[area]["blocker_severity"], "P0_BLOCKER")
            self.assertIn("INPUT_ARTIFACT_MISSING", rows[area]["reason_codes"])
            self.assertNotEqual(rows[area]["required_operator_action"], "")

    def test_sample_watchlist_is_sample_only_and_never_ready(self) -> None:
        write_summary(
            self.watchlist,
            {
                "watchlist_input_status": "SAMPLE_DEMO_ONLY",
                "watchlist_readiness_status": "BLOCKED",
                "watchlist_reason_codes": "WATCHLIST_SAMPLE_INPUT;WATCHLIST_REVIEW_OR_MISSING_DATA",
                "watchlist_rows_total": "8",
                "watchlist_sample_input_active": "True",
            },
        )
        self.write_ready_supporting_summaries()
        self.run_closure()

        watchlist = self.rows_by_area()["WATCHLIST"]
        self.assertEqual(watchlist["status"], "SAMPLE_ONLY")
        self.assertEqual(watchlist["sample_or_synthetic_flag"], "True")
        self.assertNotEqual(watchlist["status"], "READY")
        self.assertIn("Replace sample watchlist", watchlist["required_operator_action"])

    def test_valuation_missing_rows_block_readiness(self) -> None:
        write_summary(self.watchlist, {"watchlist_input_status": "PERSONAL_REVIEWED", "watchlist_readiness_status": "PASS"})
        write_summary(
            self.valuation,
            {
                "affected_standard_rows_count": "2",
                "approved_rows_count": "0",
                "input_file_status": "MISSING",
                "missing_rows_count": "2",
                "reason_codes": "INPUT_FILE_MISSING;NO_IMPUTATION;VALUATION_REQUIRED_MISSING",
                "review_rows_count": "0",
            },
        )
        write_summary(self.dividend, {"affected_standard_rows_count": "0", "approved_rows_count": "0", "input_file_status": "PRESENT", "missing_rows_count": "0", "review_rows_count": "0"})
        write_summary(self.provenance, {"provenance_incomplete_flag": "False", "provenance_status__MISSING": "0", "provenance_status__PARTIAL": "0", "provenance_status__AMBIGUOUS": "0"})
        self.run_closure()

        valuation = self.rows_by_area()["VALUATION"]
        self.assertEqual(valuation["status"], "BLOCKED")
        self.assertEqual(valuation["missing_or_review_items_count"], "2")
        self.assertIn("reviewed valuation input", valuation["required_operator_action"])

    def test_dividend_fcf_missing_rows_surface_sec_evidence_hint(self) -> None:
        write_summary(self.watchlist, {"watchlist_input_status": "PERSONAL_REVIEWED", "watchlist_readiness_status": "PASS"})
        write_summary(self.valuation, {"affected_standard_rows_count": "0", "approved_rows_count": "0", "input_file_status": "PRESENT", "missing_rows_count": "0", "review_rows_count": "0"})
        write_summary(
            self.dividend,
            {
                "affected_standard_rows_count": "3",
                "approved_rows_count": "0",
                "input_file_status": "MISSING",
                "missing_rows_count": "3",
                "reason_codes": "DIVIDEND_FCF_REQUIRED_MISSING;SEC_IDENTITY_AVAILABLE",
                "review_rows_count": "0",
                "sec_evidence_possible_count": "3",
            },
        )
        write_summary(self.provenance, {"provenance_incomplete_flag": "False", "provenance_status__MISSING": "0", "provenance_status__PARTIAL": "0", "provenance_status__AMBIGUOUS": "0"})
        self.run_closure()

        dividend = self.rows_by_area()["DIVIDEND_FCF"]
        self.assertEqual(dividend["status"], "BLOCKED")
        self.assertIn("SEC evidence is structurally possible for 3 row(s)", dividend["required_operator_action"])

    def test_kpi_provenance_gaps_are_not_ready(self) -> None:
        write_summary(self.watchlist, {"watchlist_input_status": "PERSONAL_REVIEWED", "watchlist_readiness_status": "PASS"})
        write_summary(self.valuation, {"affected_standard_rows_count": "0", "approved_rows_count": "0", "input_file_status": "PRESENT", "missing_rows_count": "0", "review_rows_count": "0"})
        write_summary(self.dividend, {"affected_standard_rows_count": "0", "approved_rows_count": "0", "input_file_status": "PRESENT", "missing_rows_count": "0", "review_rows_count": "0"})
        write_summary(
            self.provenance,
            {
                "holdings_with_incomplete_provenance_total": "2",
                "provenance_incomplete_flag": "True",
                "provenance_status__AMBIGUOUS": "1",
                "provenance_status__MISSING": "4",
                "provenance_status__PARTIAL": "1",
            },
        )
        self.run_closure()

        provenance = self.rows_by_area()["KPI_PROVENANCE"]
        self.assertEqual(provenance["status"], "BLOCKED")
        self.assertEqual(provenance["missing_or_review_items_count"], "2")
        self.assertIn("PROVENANCE_INCOMPLETE", provenance["reason_codes"])

    def test_trusted_only_kpi_provenance_can_be_ready(self) -> None:
        write_summary(self.watchlist, {"watchlist_input_status": "PERSONAL_REVIEWED", "watchlist_readiness_status": "PASS"})
        self.write_ready_supporting_summaries()
        self.run_closure()

        self.assertEqual(self.rows_by_area()["KPI_PROVENANCE"]["status"], "READY")

    def test_core_kpi_closure_is_optional_additional_area_when_summary_exists(self) -> None:
        write_summary(self.watchlist, {"watchlist_input_status": "PERSONAL_REVIEWED", "watchlist_readiness_status": "PASS"})
        self.write_ready_supporting_summaries()
        write_summary(
            self.core,
            {
                "affected_standard_rows_count": "1",
                "reason_codes": "CORE_KPI_MISSING;REVIEW_CORE_DATA;SEC_IDENTITY_AVAILABLE",
                "review_rows_count": "1",
                "sec_evidence_possible_count": "1",
            },
        )
        self.run_closure()

        core = self.rows_by_area()["CORE_KPI_CLOSURE"]
        self.assertEqual(core["status"], "BLOCKED")
        self.assertIn("additional to KPI provenance", core["downstream_impact"])

    def test_output_is_deterministic_and_has_stable_fields(self) -> None:
        write_summary(self.watchlist, {"watchlist_input_status": "PERSONAL_REVIEWED", "watchlist_readiness_status": "PASS"})
        self.write_ready_supporting_summaries()
        self.run_closure()
        first = self.output.read_text(encoding="utf-8")
        self.run_closure()
        second = self.output.read_text(encoding="utf-8")

        self.assertEqual(first, second)
        self.assertEqual(list(read_csv(self.output)[0].keys()), FIELDNAMES)
        self.assertEqual([row["input_area"] for row in read_csv(self.output)], ["WATCHLIST", "VALUATION", "DIVIDEND_FCF", "KPI_PROVENANCE"])

    def test_markdown_contains_required_sections(self) -> None:
        write_summary(self.watchlist, {"watchlist_input_status": "SAMPLE_DEMO_ONLY", "watchlist_readiness_status": "BLOCKED", "watchlist_sample_input_active": "True"})
        self.write_ready_supporting_summaries()
        self.run_closure()

        text = self.report.read_text(encoding="utf-8")
        self.assertIn("## Executive Summary", text)
        self.assertIn("## Input Closure Matrix", text)
        self.assertIn("## Operator Actions", text)
        self.assertIn("## Guardrails", text)

    def test_no_broker_order_or_trading_fields_are_emitted(self) -> None:
        write_summary(self.watchlist, {"watchlist_input_status": "PERSONAL_REVIEWED", "watchlist_readiness_status": "PASS"})
        self.write_ready_supporting_summaries()
        self.run_closure()

        forbidden = {"order_id", "broker", "execution_id", "linked_transaction_id", "filled_price", "tax_lot", "realized_gain"}
        self.assertTrue(forbidden.isdisjoint(set(read_csv(self.output)[0].keys())))

    def test_existing_input_artifacts_are_not_overwritten(self) -> None:
        write_summary(self.watchlist, {"watchlist_input_status": "PERSONAL_REVIEWED", "watchlist_readiness_status": "PASS"})
        self.write_ready_supporting_summaries()
        before = self.watchlist.read_text(encoding="utf-8")
        self.run_closure()

        self.assertEqual(self.watchlist.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
