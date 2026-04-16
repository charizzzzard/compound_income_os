from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.common import read_csv_rows
from src.fundamentals_evidence_engine import EVIDENCE_INPUT_FIELDS
from src.fundamentals_snapshot_review import (
    SNAPSHOT_REVIEW_BACKLOG_FIELDS,
    SNAPSHOT_REVIEW_INPUT_FIELDS,
    SNAPSHOT_REVIEW_REGISTRY_FIELDS,
    SNAPSHOT_REVIEW_SUMMARY_FIELDS,
    run_fundamentals_snapshot_review,
    write_snapshot_review_template,
)


def staging_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    kpi_name: str = "roic",
    source_name: str = "vendor_snapshot",
    source_reference: str = "vendor_export_2026q1",
    source_as_of_date: str = "2026-04-15",
    fiscal_year: str = "2025",
    reported_value: str = "25",
    reported_unit: str = "percent",
    currency: str = "USD",
    notes: str = "staging fixture",
) -> dict[str, str]:
    row = {field: "" for field in EVIDENCE_INPUT_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "kpi_name": kpi_name,
            "source_type": "SNAPSHOT_IMPORT",
            "source_name": source_name,
            "source_reference": source_reference,
            "source_as_of_date": source_as_of_date,
            "fiscal_year": fiscal_year,
            "verification_status": "UNVERIFIED",
            "data_quality_flag": "REVIEW",
            "notes": notes,
            "reported_value": reported_value,
            "reported_unit": reported_unit,
            "currency": currency,
        }
    )
    return row


def review_row(
    *,
    ticker: str = "MSFT",
    isin: str = "US5949181045",
    company_name: str = "Microsoft Corp",
    kpi_name: str = "roic",
    source_name: str = "vendor_snapshot",
    source_reference: str = "vendor_export_2026q1",
    source_as_of_date: str = "2026-04-15",
    fiscal_year: str = "2025",
    review_decision: str = "APPROVE",
    review_reason: str = "manual review completed",
    review_author: str = "qa_user",
    review_as_of_date: str = "2026-04-17",
    notes: str = "review fixture",
) -> dict[str, str]:
    row = {field: "" for field in SNAPSHOT_REVIEW_INPUT_FIELDS}
    row.update(
        {
            "ticker": ticker,
            "isin": isin,
            "company_name": company_name,
            "kpi_name": kpi_name,
            "source_name": source_name,
            "source_reference": source_reference,
            "source_as_of_date": source_as_of_date,
            "fiscal_year": fiscal_year,
            "review_decision": review_decision,
            "review_reason": review_reason,
            "review_author": review_author,
            "review_as_of_date": review_as_of_date,
            "notes": notes,
        }
    )
    return row


class FundamentalsSnapshotReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_paths: list[Path] = []

    def tearDown(self) -> None:
        for path in reversed(self.temp_paths):
            if path.exists():
                path.unlink()

    def _path(self, name: str) -> Path:
        path = Path("tests") / name
        self.temp_paths.append(path)
        return path

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _run_engine(
        self,
        *,
        staging_rows: list[dict[str, str]],
        review_rows: list[dict[str, str]],
        prefix: str,
    ) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
        staging_path = self._path(f"_tmp_snapshot_review_{prefix}_staging.csv")
        review_path = self._path(f"_tmp_snapshot_review_{prefix}_input.csv")
        registry_path = self._path(f"_tmp_snapshot_review_{prefix}_registry.csv")
        promoted_path = self._path(f"_tmp_snapshot_review_{prefix}_promoted.csv")
        backlog_path = self._path(f"_tmp_snapshot_review_{prefix}_backlog.csv")
        summary_path = self._path(f"_tmp_snapshot_review_{prefix}_summary.csv")
        template_path = self._path(f"_tmp_snapshot_review_{prefix}_template.csv")
        self._write_csv(staging_path, EVIDENCE_INPUT_FIELDS, staging_rows)
        self._write_csv(review_path, SNAPSHOT_REVIEW_INPUT_FIELDS, review_rows)
        run_fundamentals_snapshot_review(
            staging_input_path=str(staging_path),
            review_input_path=str(review_path),
            registry_output=str(registry_path),
            promoted_output=str(promoted_path),
            backlog_output=str(backlog_path),
            summary_output=str(summary_path),
            template_output=str(template_path),
        )
        return staging_path, review_path, registry_path, promoted_path, backlog_path, summary_path, template_path

    def test_valid_review_promotes_approved_staging_rows(self) -> None:
        _staging, _review, registry_path, promoted_path, backlog_path, summary_path, template_path = self._run_engine(
            staging_rows=[staging_row()],
            review_rows=[review_row()],
            prefix="approved",
        )

        registry_rows = read_csv_rows(registry_path)
        promoted_rows = read_csv_rows(promoted_path)
        backlog_rows = read_csv_rows(backlog_path)
        summary_rows = read_csv_rows(summary_path)
        self.assertEqual(len(registry_rows), 1)
        self.assertEqual(registry_rows[0]["promotion_status"], "PROMOTED")
        self.assertEqual(len(promoted_rows), 1)
        self.assertEqual(promoted_rows[0]["kpi_name"], "roic")
        self.assertIn("snapshot_review_decision=APPROVE", promoted_rows[0]["notes"])
        self.assertEqual(backlog_rows, [])
        self.assertEqual(summary_rows[0]["approved_rows"], "1")
        self.assertEqual(summary_rows[0]["promoted_rows"], "1")
        with template_path.open("r", encoding="utf-8", newline="") as handle:
            self.assertEqual(next(csv.reader(handle)), SNAPSHOT_REVIEW_INPUT_FIELDS)

    def test_pending_and_reject_do_not_generate_promoted_rows(self) -> None:
        _staging, _review, registry_path, promoted_path, backlog_path, summary_path, _template_path = self._run_engine(
            staging_rows=[
                staging_row(kpi_name="roic"),
                staging_row(kpi_name="fcf_margin", reported_value="30"),
            ],
            review_rows=[
                review_row(kpi_name="roic", review_decision="PENDING", review_reason="awaiting second check"),
                review_row(kpi_name="fcf_margin", review_decision="REJECT", review_reason="stale vendor value"),
            ],
            prefix="pending_reject",
        )

        registry_rows = read_csv_rows(registry_path)
        promoted_rows = read_csv_rows(promoted_path)
        backlog_rows = read_csv_rows(backlog_path)
        summary_rows = read_csv_rows(summary_path)
        self.assertEqual({row["promotion_status"] for row in registry_rows}, {"PENDING", "REJECTED"})
        self.assertEqual(promoted_rows, [])
        self.assertEqual(len(backlog_rows), 1)
        self.assertEqual(backlog_rows[0]["backlog_status"], "PENDING")
        self.assertEqual(summary_rows[0]["pending_rows"], "1")
        self.assertEqual(summary_rows[0]["rejected_rows"], "1")
        self.assertEqual(summary_rows[0]["promoted_rows"], "0")

    def test_conflicting_review_decisions_for_same_staging_identity_fail_fast(self) -> None:
        with self.assertRaisesRegex(ValueError, "conflicting duplicate snapshot review identity"):
            self._run_engine(
                staging_rows=[staging_row()],
                review_rows=[
                    review_row(review_decision="APPROVE"),
                    review_row(review_decision="REJECT", review_reason="conflicting decision"),
                ],
                prefix="conflict",
            )

    def test_review_without_matching_staging_row_fails_fast(self) -> None:
        with self.assertRaisesRegex(ValueError, "has no matching staging row"):
            self._run_engine(
                staging_rows=[staging_row()],
                review_rows=[review_row(kpi_name="fcf_margin", review_reason="wrong kpi identity")],
                prefix="missing_staging",
            )

    def test_promoted_rows_follow_existing_evidence_contract_without_verified_upgrade(self) -> None:
        _staging, _review, _registry_path, promoted_path, _backlog_path, _summary_path, _template_path = self._run_engine(
            staging_rows=[staging_row()],
            review_rows=[review_row()],
            prefix="contract",
        )

        promoted_rows = read_csv_rows(promoted_path)
        self.assertEqual(set(promoted_rows[0]), set(EVIDENCE_INPUT_FIELDS))
        self.assertTrue(all(row["source_type"] == "SNAPSHOT_IMPORT" for row in promoted_rows))
        self.assertTrue(all(row["verification_status"] == "UNVERIFIED" for row in promoted_rows))
        self.assertTrue(all(row["data_quality_flag"] == "REVIEW" for row in promoted_rows))
        self.assertEqual(SNAPSHOT_REVIEW_REGISTRY_FIELDS[0], "ticker")
        self.assertEqual(SNAPSHOT_REVIEW_BACKLOG_FIELDS[0], "ticker")
        self.assertEqual(SNAPSHOT_REVIEW_SUMMARY_FIELDS[0], "staging_rows_total")

    def test_review_template_writer_creates_header_only_template(self) -> None:
        template_path = self._path("_tmp_snapshot_review_template_only.csv")

        write_snapshot_review_template(str(template_path))

        with template_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, SNAPSHOT_REVIEW_INPUT_FIELDS)
            self.assertEqual(list(reader), [])


if __name__ == "__main__":
    unittest.main()
