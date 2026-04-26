from __future__ import annotations

import shutil
import unittest
import zipfile
from pathlib import Path

from src.handoff_zip_export import export_handoff_zip, scan_forbidden_entries


ROOT = Path(__file__).resolve().parent.parent


class HandoffZipExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_paths: list[Path] = []
        self.preserved_files: dict[Path, bytes | None] = {}

    def tearDown(self) -> None:
        for path in reversed(self.temp_paths):
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        for path, content in self.preserved_files.items():
            if content is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)

    def _path(self, name: str) -> Path:
        path = Path("tests") / name
        self.temp_paths.append(path)
        return path

    def _write_preserved_file(self, path: Path, content: str) -> None:
        if path not in self.preserved_files:
            self.preserved_files[path] = path.read_bytes() if path.exists() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_export_contains_metadata_and_excludes_forbidden_entries(self) -> None:
        result = export_handoff_zip(output_dir="tests")
        self.temp_paths.append(result.zip_path)

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())

        self.assertIn("ZIP_REPO_HEAD.txt", names)
        self.assertIn("ZIP_REPO_STATUS.txt", names)
        self.assertTrue(any(name.startswith("src/") for name in names))
        self.assertTrue(any(name.startswith("tests/") for name in names))
        if (ROOT / "website").exists():
            self.assertTrue(any(name.startswith("website/") for name in names))
        self.assertEqual(result.forbidden_matches, ())
        self.assertEqual(scan_forbidden_entries(result.zip_path), ())

    def test_export_contains_explicit_handoff_artifacts_without_opening_reports_broadly(self) -> None:
        artifact_paths = [
            ROOT / "data" / "processed" / "personal_profile_review_unlock_summary.csv",
            ROOT / "data" / "processed" / "personal_profile_review_unlock_holdings.csv",
            ROOT / "data" / "processed" / "personal_missing_kpi_closure_summary.csv",
            ROOT / "data" / "processed" / "personal_missing_kpi_closure_holdings.csv",
            ROOT / "data" / "processed" / "personal_evidence_applied_downstream_delta_summary.csv",
            ROOT / "data" / "processed" / "personal_evidence_applied_downstream_delta_holdings.csv",
            ROOT / "data" / "processed" / "personal_artifact_reconciliation_summary.csv",
            ROOT / "data" / "processed" / "personal_artifact_reconciliation_checks.csv",
            ROOT / "data" / "processed" / "personal_kpi_provenance_audit.csv",
            ROOT / "data" / "processed" / "personal_kpi_provenance_summary.csv",
            ROOT / "reports" / "2099-01-01" / "personal_profile_review_unlock_report.md",
            ROOT / "reports" / "2099-01-01" / "personal_missing_kpi_closure_report.md",
            ROOT / "reports" / "2099-01-01" / "personal_evidence_applied_downstream_delta_report.md",
            ROOT / "reports" / "2099-01-01" / "strategy_review_fundamentals_trust_scoring.md",
            ROOT / "reports" / "2099-01-01" / "personal_artifact_reconciliation_report.md",
            ROOT / "reports" / "2099-01-01" / "personal_kpi_provenance_audit_report.md",
            ROOT / "reports" / "2099-01-01" / "historical_report.md",
        ]
        for path in artifact_paths:
            self._write_preserved_file(path, "metric,value\nexample,1\n")
        self.temp_paths.append(ROOT / "reports" / "2099-01-01")

        result = export_handoff_zip(output_dir="tests")
        self.temp_paths.append(result.zip_path)

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())

        self.assertIn("data/processed/personal_profile_review_unlock_summary.csv", names)
        self.assertIn("data/processed/personal_profile_review_unlock_holdings.csv", names)
        self.assertIn("data/processed/personal_missing_kpi_closure_summary.csv", names)
        self.assertIn("data/processed/personal_missing_kpi_closure_holdings.csv", names)
        self.assertIn("data/processed/personal_evidence_applied_downstream_delta_summary.csv", names)
        self.assertIn("data/processed/personal_evidence_applied_downstream_delta_holdings.csv", names)
        self.assertIn("data/processed/personal_artifact_reconciliation_summary.csv", names)
        self.assertIn("data/processed/personal_artifact_reconciliation_checks.csv", names)
        self.assertIn("data/processed/personal_kpi_provenance_audit.csv", names)
        self.assertIn("data/processed/personal_kpi_provenance_summary.csv", names)
        self.assertIn("reports/2099-01-01/personal_profile_review_unlock_report.md", names)
        self.assertIn("reports/2099-01-01/personal_missing_kpi_closure_report.md", names)
        self.assertIn("reports/2099-01-01/personal_evidence_applied_downstream_delta_report.md", names)
        self.assertIn("reports/2099-01-01/strategy_review_fundamentals_trust_scoring.md", names)
        self.assertIn("reports/2099-01-01/personal_artifact_reconciliation_report.md", names)
        self.assertIn("reports/2099-01-01/personal_kpi_provenance_audit_report.md", names)
        self.assertNotIn("reports/2099-01-01/historical_report.md", names)
        self.assertEqual(scan_forbidden_entries(result.zip_path), ())

    def test_forbidden_entry_scan_detects_blocked_paths(self) -> None:
        zip_path = self._path("_tmp_handoff_bad.zip")
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr(".git/config", "blocked")
            archive.writestr("reports/run.md", "blocked")
            archive.writestr("reports/2026-04-26/personal_profile_review_unlock_report.md", "allowed")
            archive.writestr("reports/2026-04-26/personal_missing_kpi_closure_report.md", "allowed")
            archive.writestr("reports/2026-04-26/personal_evidence_applied_downstream_delta_report.md", "allowed")
            archive.writestr("reports/2026-04-26/strategy_review_fundamentals_trust_scoring.md", "allowed")
            archive.writestr("reports/2026-04-26/personal_artifact_reconciliation_report.md", "allowed")
            archive.writestr("reports/2026-04-26/personal_kpi_provenance_audit_report.md", "allowed")
            archive.writestr("data/raw/private/secret.csv", "blocked")
            archive.writestr("tests/_tmp_fixture.csv", "blocked")
            archive.writestr("src/__pycache__/module.pyc", "blocked")
            archive.writestr("old_export.zip", "blocked")
            archive.writestr("website/compound-income-os-landing/.env", "blocked")
            archive.writestr("website/compound-income-os-landing/.env.production.local", "blocked")
            archive.writestr("website/compound-income-os-landing/.env.example", "allowed")
            archive.writestr("website/compound-income-os-landing/deploy_artifacts/dist.zip", "blocked")
            archive.writestr("src/app.py", "allowed")

        matches = scan_forbidden_entries(zip_path)

        self.assertIn(".git/config", matches)
        self.assertIn("reports/run.md", matches)
        self.assertNotIn("reports/2026-04-26/personal_profile_review_unlock_report.md", matches)
        self.assertNotIn("reports/2026-04-26/personal_missing_kpi_closure_report.md", matches)
        self.assertNotIn("reports/2026-04-26/personal_evidence_applied_downstream_delta_report.md", matches)
        self.assertNotIn("reports/2026-04-26/strategy_review_fundamentals_trust_scoring.md", matches)
        self.assertNotIn("reports/2026-04-26/personal_artifact_reconciliation_report.md", matches)
        self.assertNotIn("reports/2026-04-26/personal_kpi_provenance_audit_report.md", matches)
        self.assertIn("data/raw/private/secret.csv", matches)
        self.assertIn("tests/_tmp_fixture.csv", matches)
        self.assertIn("src/__pycache__/module.pyc", matches)
        self.assertIn("old_export.zip", matches)
        self.assertIn("website/compound-income-os-landing/.env", matches)
        self.assertIn("website/compound-income-os-landing/.env.production.local", matches)
        self.assertNotIn("website/compound-income-os-landing/.env.example", matches)
        self.assertIn("website/compound-income-os-landing/deploy_artifacts/dist.zip", matches)
        self.assertNotIn("src/app.py", matches)


if __name__ == "__main__":
    unittest.main()
