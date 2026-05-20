from __future__ import annotations

import csv
import shutil
import unittest
import zipfile
from pathlib import Path

from src.handoff_zip_export import (
    export_handoff_zip,
    export_profile_handoff_zip,
    scan_forbidden_entries,
    scan_local_path_leaks_in_zip,
)


ROOT = Path(__file__).resolve().parent.parent


class HandoffZipExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "handoff_zip_export_fixture"
        self.tmp.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def test_preview_export_keeps_legacy_entrypoint_with_unified_metadata(self) -> None:
        result = export_handoff_zip(output_dir=self.tmp)

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())
            validation_text = archive.read("HANDOFF_VALIDATION.txt").decode("utf-8")
            manifest_rows = list(csv.DictReader(archive.read("HANDOFF_MANIFEST.csv").decode("utf-8").splitlines()))

        self.assertIn("HANDOFF_CONTEXT.md", names)
        self.assertIn("HANDOFF_REPORT.md", names)
        self.assertIn("HANDOFF_MANIFEST.csv", names)
        self.assertIn("HANDOFF_CHANGE_CLASSIFICATION.csv", names)
        self.assertIn("HANDOFF_VALIDATION.txt", names)
        self.assertTrue(any(name.startswith("src/") for name in names))
        self.assertTrue(any(name.startswith("tests/") for name in names))
        self.assertNotIn("ZIP_REPO_HEAD.txt", names)
        self.assertNotIn("HANDOFF_preview_preview_", result.zip_path.name)
        self.assertIn(f"file_count={len(names)}", validation_text)
        self.assertIn("forbidden_count=0", validation_text)
        self.assertIn("nested_zip_count=0", validation_text)
        self.assertIn("manifest_file_count_delta=2", validation_text)
        self.assertEqual(len(names) - len(manifest_rows), 2)
        self.assertEqual(result.forbidden_matches, ())
        self.assertEqual(scan_forbidden_entries(result.zip_path), ())
        self.assertEqual(scan_local_path_leaks_in_zip(result.zip_path), ())

    def test_patch_profile_contains_known_sec_concept_review_artifacts(self) -> None:
        result = export_profile_handoff_zip(
            profile="patch",
            name="sec_companyfacts_concept_review",
            output_dir=self.tmp,
            validation_summary="unit validation",
        )

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())
            context_text = archive.read("HANDOFF_CONTEXT.md").decode("utf-8")
            omitted_text = archive.read("HANDOFF_OMITTED_ARTIFACTS.csv").decode("utf-8")

        expected = {
            "_archive/sec/src/personal_sec_kpi_extraction_gap_review.py",
            "_archive/sec/tests/test_personal_sec_kpi_extraction_gap_review.py",
            "data/processed/personal_sec_kpi_extraction_gap_matrix.csv",
            "data/processed/personal_sec_kpi_extraction_concept_candidates.csv",
            "data/processed/personal_sec_kpi_extraction_gap_summary.csv",
            "reports/2026-04-27/personal_sec_kpi_extraction_gap_review_report.md",
            "_archive/sec/src/personal_sec_companyfacts_concept_review_table.py",
            "_archive/sec/tests/test_personal_sec_companyfacts_concept_review_table.py",
            "data/processed/personal_sec_companyfacts_concept_review_table.csv",
            "data/processed/personal_sec_companyfacts_concept_review_summary.csv",
            "reports/2026-04-27/personal_sec_companyfacts_concept_review_table_report.md",
        }
        self.assertTrue(expected.issubset(names))
        self.assertIn("profile: `patch`", context_text)
        self.assertNotIn("data/raw/private/fundamentals/personal_sec_companyfacts_concept_approval_template.csv", names)
        self.assertNotIn("sec_user_agent.local.txt", "\n".join(names))
        self.assertIn("<private_raw_file>", omitted_text)
        self.assertEqual(scan_forbidden_entries(result.zip_path), ())

    def test_explicit_forbidden_include_is_omitted_not_included(self) -> None:
        forbidden = ROOT / "data" / "raw" / "private" / "fundamentals" / "sec_user_agent.local.txt"
        result = export_profile_handoff_zip(
            profile="patch",
            name="unit_forbidden",
            output_dir=self.tmp,
            include_paths=[str(forbidden)],
        )

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())
            omitted_rows = list(csv.DictReader(archive.read("HANDOFF_OMITTED_ARTIFACTS.csv").decode("utf-8").splitlines()))

        self.assertNotIn("data/raw/private/fundamentals/sec_user_agent.local.txt", names)
        self.assertTrue(any(row["omission_reason"] == "FORBIDDEN_PATH" for row in omitted_rows))
        self.assertEqual(scan_forbidden_entries(result.zip_path), ())

    def test_explicit_include_self_handoff_contains_handoff_system_files_and_validation(self) -> None:
        include_paths = [
            "src/handoff_bundle.py",
            "src/handoff_zip_export.py",
            "src/patch_handoff_export.py",
            "tests/test_handoff_bundle.py",
            "tests/test_handoff_zip_export.py",
            "tests/test_patch_handoff_export.py",
            "docs/HANDOFF_CONTRACT.md",
            "docs/CODEX_TASKS/POST_ITERATION_QA.md",
        ]
        result = export_profile_handoff_zip(
            profile="patch",
            name="unified_handoff_export_system",
            output_dir=self.tmp,
            include_paths=include_paths,
            validation_commands=["python -m unittest tests.test_handoff_bundle -q"],
        )

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())
            validation_text = archive.read("HANDOFF_VALIDATION.txt").decode("utf-8")

        self.assertTrue(set(include_paths).issubset(names))
        self.assertIn("HANDOFF_CONTEXT.md", names)
        self.assertIn("HANDOFF_REPORT.md", names)
        self.assertIn("python -m unittest tests.test_handoff_bundle -q", validation_text)
        self.assertIn("manifest_sha256=", validation_text)
        self.assertNotIn("data/raw/private/", "\n".join(names))
        self.assertNotIn("sec_user_agent.local.txt", "\n".join(names))
        self.assertFalse(any(name.endswith(".zip") for name in names))
        self.assertEqual(scan_forbidden_entries(result.zip_path), ())

    def test_forbidden_entry_scan_detects_blocked_paths_and_allows_known_reports(self) -> None:
        zip_path = self.tmp / "bad_scan.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr(".git/config", "blocked")
            archive.writestr("reports/run.md", "blocked")
            archive.writestr("reports/2026-04-27/personal_sec_kpi_extraction_gap_review_report.md", "allowed")
            archive.writestr("data/raw/private/secret.csv", "blocked")
            archive.writestr("old_export.zip", "blocked")
            archive.writestr("website/compound-income-os-landing/.env", "blocked")
            archive.writestr("website/compound-income-os-landing/.env.example", "allowed")
            archive.writestr("src/__pycache__/app.cpython-313.pyc", "blocked")
            archive.writestr("src/.pytest_cache/v/cache/nodeids", "blocked")
            archive.writestr("src/.mypy_cache/meta.json", "blocked")
            archive.writestr("src/.ruff_cache/cache.bin", "blocked")
            archive.writestr("src/.cache/tool/cache.bin", "blocked")
            archive.writestr("src/.DS_Store", "blocked")
            archive.writestr("src/Thumbs.db", "blocked")
            archive.writestr("src/app.py", "allowed")

        matches = scan_forbidden_entries(zip_path)

        self.assertIn(".git/config", matches)
        self.assertIn("reports/run.md", matches)
        self.assertNotIn("reports/2026-04-27/personal_sec_kpi_extraction_gap_review_report.md", matches)
        self.assertIn("data/raw/private/secret.csv", matches)
        self.assertIn("old_export.zip", matches)
        self.assertIn("website/compound-income-os-landing/.env", matches)
        self.assertIn("website/compound-income-os-landing/.env.example", matches)
        self.assertIn("src/__pycache__/app.cpython-313.pyc", matches)
        self.assertIn("src/.pytest_cache/v/cache/nodeids", matches)
        self.assertIn("src/.mypy_cache/meta.json", matches)
        self.assertIn("src/.ruff_cache/cache.bin", matches)
        self.assertIn("src/.cache/tool/cache.bin", matches)
        self.assertIn("src/.DS_Store", matches)
        self.assertIn("src/Thumbs.db", matches)
        self.assertNotIn("src/app.py", matches)

    def test_full_review_export_omits_cache_directories_and_os_metadata(self) -> None:
        cache_root = self.tmp / "cache_source"
        (cache_root / "__pycache__").mkdir(parents=True)
        (cache_root / "__pycache__" / "mod.cpython-313.pyc").write_bytes(b"cache")
        (cache_root / ".pytest_cache" / "v" / "cache").mkdir(parents=True)
        (cache_root / ".pytest_cache" / "v" / "cache" / "nodeids").write_text("cache", encoding="utf-8")
        (cache_root / ".mypy_cache").mkdir(parents=True)
        (cache_root / ".mypy_cache" / "meta.json").write_text("{}", encoding="utf-8")
        (cache_root / ".ruff_cache").mkdir(parents=True)
        (cache_root / ".ruff_cache" / "cache.bin").write_bytes(b"cache")
        (cache_root / ".cache" / "tool").mkdir(parents=True)
        (cache_root / ".cache" / "tool" / "cache.bin").write_bytes(b"cache")
        (cache_root / ".DS_Store").write_bytes(b"cache")
        (cache_root / "Thumbs.db").write_bytes(b"cache")
        (cache_root / "safe.txt").write_text("safe", encoding="utf-8")

        result = export_profile_handoff_zip(profile="full_review", name="unit_cache_hygiene", output_dir=self.tmp)

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())

        joined = "\n".join(sorted(names))
        self.assertIn("tests/handoff_zip_export_fixture/cache_source/safe.txt", names)
        self.assertIn(".gitattributes", names)
        self.assertNotIn("__pycache__", joined)
        self.assertFalse(any(name.endswith(".pyc") for name in names))
        self.assertNotIn(".pytest_cache", joined)
        self.assertNotIn(".mypy_cache", joined)
        self.assertNotIn(".ruff_cache", joined)
        self.assertNotIn("/.cache/", joined)
        self.assertFalse(any(name.endswith("/.DS_Store") or name.endswith("/Thumbs.db") for name in names))
        self.assertEqual(scan_forbidden_entries(result.zip_path), ())
        self.assertEqual(scan_local_path_leaks_in_zip(result.zip_path), ())

    def test_full_review_export_contains_no_local_absolute_user_paths(self) -> None:
        result = export_profile_handoff_zip(profile="full_review", name="unit_privacy_hygiene", output_dir=self.tmp)

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())

        self.assertIn(".gitattributes", names)
        self.assertNotIn("data/processed/website_static_build_package_qa.csv", names)
        self.assertNotIn("data/processed/website_static_build_package_summary.csv", names)
        self.assertFalse(any(name.endswith("/website_static_build_package_report.md") for name in names))
        self.assertEqual(scan_local_path_leaks_in_zip(result.zip_path), ())

    def test_full_review_export_uses_current_canonical_vision_only(self) -> None:
        result = export_profile_handoff_zip(profile="full_review", name="unit_canonical_vision", output_dir=self.tmp)

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())

        self.assertIn("docs/COMPOUND_INCOME_OS_VISION_v1_2.md", names)
        self.assertNotIn("docs/COMPOUND_INCOME_OS_VISION_v1_1.md", names)
        self.assertNotIn("docs/COMPOUND_INCOME_OS_VISION_v1.md", names)

    def test_docs_describe_upload_ready_handoff_usage(self) -> None:
        contract_text = (ROOT / "docs" / "HANDOFF_CONTRACT.md").read_text(encoding="utf-8")
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = "\n".join([contract_text, readme_text]).lower()

        self.assertIn("upload_ready", combined)
        self.assertIn("handoff_latest.zip", combined)
        self.assertIn("unique", combined)
        self.assertIn("external llm", combined)


if __name__ == "__main__":
    unittest.main()
