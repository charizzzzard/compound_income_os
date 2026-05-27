from __future__ import annotations

import csv
import shutil
import unittest
import zipfile
from pathlib import Path

from src.handoff_bundle import (
    STANDARD_HANDOFF_ENTRIES,
    change_classification_rows,
    export_handoff_bundle,
    is_forbidden_entry,
    parse_git_status_short_line,
    scan_forbidden_entries,
    scan_local_path_leaks_in_zip,
    sanitize_path_for_external,
    sha256_file,
    upload_bundle_id_from_context,
    validate_handoff_archive,
    validate_latest_handoff,
    validate_upload_ready_handoff,
    write_latest_handoff_files,
    write_upload_ready_handoff_files,
)


ROOT = Path(__file__).resolve().parent.parent


class HandoffBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = ROOT / "tests" / "handoff_bundle_fixture"
        self.fixture.mkdir(parents=True, exist_ok=True)
        self.safe_file = self.fixture / "artifact.txt"
        self.safe_file.write_text("artifact\n", encoding="utf-8")
        self.private_file = ROOT / "data" / "raw" / "private" / "fundamentals" / "sec_user_agent.local.txt"
        self.nested_zip = self.fixture / "nested.zip"
        self.nested_zip.write_bytes(b"not a real handoff")
        self.node_file = ROOT / "node_modules" / "blocked.txt"

    def tearDown(self) -> None:
        if self.fixture.exists():
            shutil.rmtree(self.fixture)

    def test_forbidden_rules_block_private_user_agent_zips_and_build_dirs(self) -> None:
        self.assertTrue(is_forbidden_entry("data/raw/private/fundamentals/secret.csv"))
        self.assertTrue(is_forbidden_entry("data/raw/private/fundamentals/sec_user_agent.local.txt"))
        self.assertTrue(is_forbidden_entry("handoff.zip"))
        self.assertTrue(is_forbidden_entry("node_modules/pkg/index.js"))
        self.assertTrue(is_forbidden_entry("dist/index.html"))
        self.assertTrue(is_forbidden_entry("deploy_artifacts/build.json"))
        self.assertFalse(is_forbidden_entry("src/handoff_bundle.py"))

    def test_blocklist_wins_against_explicit_include_and_is_documented(self) -> None:
        result = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_bundle",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file, self.private_file, self.nested_zip, self.node_file],
            validation_summary="unit validation",
        )

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())
            omitted_text = archive.read("HANDOFF_OMITTED_ARTIFACTS.csv").decode("utf-8")
            classification_text = archive.read("HANDOFF_CHANGE_CLASSIFICATION.csv").decode("utf-8")

        self.assertIn("tests/handoff_bundle_fixture/artifact.txt", names)
        self.assertNotIn("data/raw/private/fundamentals/sec_user_agent.local.txt", names)
        self.assertNotIn("tests/handoff_bundle_fixture/nested.zip", names)
        self.assertEqual(scan_forbidden_entries(result.zip_path), ())
        self.assertIn("FORBIDDEN_PATH", omitted_text)
        self.assertIn("<user_agent_file>", omitted_text)
        self.assertNotIn("sec_user_agent.local.txt", classification_text)

    def test_handoff_zip_content_scan_detects_local_user_paths(self) -> None:
        zip_path = self.fixture / "content_leak.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("data/processed/leak.csv", "path\nC:\\Users\\Operator\\Documents\\secret.csv\n")
            archive.writestr("src/path_rules.py", 'WINDOWS_ABSOLUTE_RE = r"^[A-Za-z]:[\\\\/]"\n')
            archive.writestr("tests/test_path_sanitizer.py", "SYNTHETIC = r'C:\\Users\\Max\\private.csv'\n")

        findings = scan_local_path_leaks_in_zip(zip_path)

        self.assertIn("data/processed/leak.csv:LOCAL_WINDOWS_USER_PATH", findings)
        self.assertFalse(any(finding.startswith("src/path_rules.py") for finding in findings))
        self.assertFalse(any(finding.startswith("tests/test_path_sanitizer.py") for finding in findings))

    def test_source_scan_detects_current_operator_paths_without_hardcoded_user(self) -> None:
        source = (ROOT / "src" / "handoff_bundle.py").read_text(encoding="utf-8")
        self.assertNotIn("sc_" + "mprinsen", source)

        zip_path = self.fixture / "operator_source_leak.zip"
        current_user = Path.home().name or "operator"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr(
                "src/local_path_leak.py",
                f'LOCAL_PATH = r"C:\\Users\\{current_user}\\Documents\\secret.csv"\n',
            )
            archive.writestr("tests/test_synthetic_paths.py", "SYNTHETIC = r'C:\\Users\\Max\\private.csv'\n")

        findings = scan_local_path_leaks_in_zip(zip_path)

        self.assertIn("src/local_path_leak.py:REAL_OPERATOR_LOCAL_PATH", findings)
        self.assertFalse(any(finding.startswith("tests/test_synthetic_paths.py") for finding in findings))

    def test_content_scan_allows_synthetic_test_fixtures_without_allowing_productive_leaks(self) -> None:
        zip_path = self.fixture / "synthetic_fixture_scan.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("tests/test_synthetic_paths.py", "SYNTHETIC = r'C:\\Users\\Max\\private.csv'\n")
            archive.writestr("reports/2026-05-20/leak.md", "Local package: \\\\server\\share\\deploy.zip\n")

        findings = scan_local_path_leaks_in_zip(zip_path)

        self.assertEqual(findings, ("reports/2026-05-20/leak.md:LOCAL_UNC_PATH",))

    def test_manifest_has_stable_order_and_sha256(self) -> None:
        result = export_handoff_bundle(
            profile="manifest_only",
            bundle_name="unit_manifest",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            names = set(archive.namelist())
            manifest_rows = list(csv.DictReader(archive.read("HANDOFF_MANIFEST.csv").decode("utf-8").splitlines()))

        for entry in STANDARD_HANDOFF_ENTRIES:
            self.assertIn(entry, names)
        manifest_names = [row["entry_name"] for row in manifest_rows]
        self.assertEqual(manifest_names, sorted(manifest_names))
        self.assertTrue(all(row["sha256"] for row in manifest_rows))
        self.assertNotIn("HANDOFF_MANIFEST.csv", manifest_names)
        self.assertNotIn("HANDOFF_VALIDATION.txt", manifest_names)

    def test_git_status_parser_preserves_paths_and_renames(self) -> None:
        cases = {
            " M README.md": ("M", "README.md"),
            "M  src/file.py": ("M", "src/file.py"),
            "A  docs/new.md": ("A", "docs/new.md"),
            "?? file.txt": ("??", "file.txt"),
            "R  old.md -> new.md": ("R", "old.md -> new.md"),
        }
        for line, expected in cases.items():
            self.assertEqual(parse_git_status_short_line(line), expected)

        rows = change_classification_rows(" M README.md\n?? data/raw/private/secret.csv\n", set())
        self.assertEqual(rows[0]["path"], "README.md")
        self.assertEqual(rows[1]["path"], "<private_raw_file>")

    def test_sanitization_masks_sensitive_paths_without_damaging_normal_paths(self) -> None:
        self.assertEqual(sanitize_path_for_external("README.md"), "README.md")
        self.assertEqual(sanitize_path_for_external("src/handoff_bundle.py"), "src/handoff_bundle.py")
        self.assertEqual(sanitize_path_for_external("data/raw/private/fundamentals/secret.csv"), "<private_raw_file>")
        self.assertEqual(sanitize_path_for_external("data/raw/private/fundamentals/sec_user_agent.local.txt"), "<user_agent_file>")

    def test_validation_records_commands_and_manifest_hash_name(self) -> None:
        result = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_validation",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
            validation_commands=["python -m compileall src tests", "git diff --check"],
            validation_summary="unit validation",
        )

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            validation_text = archive.read("HANDOFF_VALIDATION.txt").decode("utf-8")

        self.assertIn("commands_run:", validation_text)
        self.assertIn("python -m compileall src tests", validation_text)
        self.assertIn("status: RECORDED", validation_text)
        self.assertIn("validation_results:", validation_text)
        self.assertIn("file_count=", validation_text)
        self.assertIn("forbidden_count=", validation_text)
        self.assertIn("nested_zip_count=", validation_text)
        self.assertIn("context_match=", validation_text)
        self.assertIn("sha256_verified=", validation_text)
        self.assertIn("latest_archive_hash_match=", validation_text)
        self.assertIn("validation_status=", validation_text)
        self.assertIn("manifest_sha256=", validation_text)
        self.assertIn("manifest_row_count=", validation_text)
        self.assertIn("terminal_metadata_count=2", validation_text)
        self.assertIn("manifest_file_count_delta=2", validation_text)
        self.assertIn("manifest_file_count_note=", validation_text)
        self.assertNotIn("sha256_scope=", validation_text)
        self.assertNotIn("\nsha256=", validation_text)

    def test_self_validation_replaces_empty_command_list(self) -> None:
        result = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_self_validation",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )

        with zipfile.ZipFile(result.zip_path, "r") as archive:
            validation_text = archive.read("HANDOFF_VALIDATION.txt").decode("utf-8")

        self.assertIn("command: self_validation_only", validation_text)
        self.assertNotIn("- none", validation_text)
        self.assertNotIn("No validation commands provided", validation_text)
        self.assertIn("zip_integrity=OK", validation_text)
        self.assertIn("nested_zip_count=0", validation_text)

    def test_latest_validation_detects_external_internal_context_mismatch(self) -> None:
        result = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_context_mismatch",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )
        latest_dir = self.fixture / "latest_mismatch"
        latest_dir.mkdir()
        with zipfile.ZipFile(result.zip_path, "r") as archive:
            context = archive.read("HANDOFF_CONTEXT.md")
        (latest_dir / "HANDOFF_LATEST.zip").write_bytes(result.zip_path.read_bytes())
        (latest_dir / "HANDOFF_LATEST_CONTEXT.md").write_bytes(context.replace(b"unit_context_mismatch", b"stale_context"))
        (latest_dir / "HANDOFF_LATEST.sha256").write_text(f"{sha256_file(result.zip_path)}  HANDOFF_LATEST.zip\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "context does not match"):
            validate_latest_handoff(latest_dir, archive_zip_path=result.zip_path)

    def test_archive_validation_detects_reported_file_count_mismatch(self) -> None:
        result = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_file_count",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )
        tampered = self.fixture / "tampered_file_count.zip"
        with zipfile.ZipFile(result.zip_path, "r") as source, zipfile.ZipFile(tampered, "w") as target:
            for info in source.infolist():
                content = source.read(info.filename)
                if info.filename == "HANDOFF_VALIDATION.txt":
                    content = content.replace(b"file_count=", b"file_count=999")
                target.writestr(info, content)

        with self.assertRaisesRegex(ValueError, "file_count mismatch"):
            validate_handoff_archive(tampered)

    def test_latest_validation_detects_sha_and_archive_hash_mismatches(self) -> None:
        result = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_hash_mismatch",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )
        latest_dir = self.fixture / "latest_hash"
        latest_dir.mkdir()
        with zipfile.ZipFile(result.zip_path, "r") as archive:
            context = archive.read("HANDOFF_CONTEXT.md")
        (latest_dir / "HANDOFF_LATEST.zip").write_bytes(result.zip_path.read_bytes())
        (latest_dir / "HANDOFF_LATEST_CONTEXT.md").write_bytes(context)
        (latest_dir / "HANDOFF_LATEST.sha256").write_text("0" * 64 + "  HANDOFF_LATEST.zip\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "SHA256"):
            validate_latest_handoff(latest_dir, archive_zip_path=result.zip_path)

        (latest_dir / "HANDOFF_LATEST.sha256").write_text(f"{sha256_file(result.zip_path)}  HANDOFF_LATEST.zip\n", encoding="utf-8")
        other_archive = self.fixture / "other_archive.zip"
        other_archive.write_bytes(b"not the same archive")
        with self.assertRaisesRegex(ValueError, "archive copy hash"):
            validate_latest_handoff(latest_dir, archive_zip_path=other_archive)

    def test_archive_validation_detects_nested_zip_and_forbidden_entries(self) -> None:
        result = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_forbidden_archive",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )
        tampered = self.fixture / "tampered_forbidden.zip"
        with zipfile.ZipFile(result.zip_path, "r") as source, zipfile.ZipFile(tampered, "w") as target:
            names = source.namelist()
            for info in source.infolist():
                content = source.read(info.filename)
                if info.filename == "HANDOFF_VALIDATION.txt":
                    content = content.replace(
                        f"file_count={len(names)}".encode("utf-8"),
                        f"file_count={len(names) + 1}".encode("utf-8"),
                    ).replace(b"forbidden_count=0", b"forbidden_count=1")
                target.writestr(info, content)
            target.writestr("nested.zip", b"blocked")

        with self.assertRaisesRegex(ValueError, "forbidden entries|nested"):
            validate_handoff_archive(tampered)

    def test_docs_describe_atomic_handoff_validation_contract(self) -> None:
        handoff_contract = (ROOT / "docs" / "HANDOFF_CONTRACT.md").read_text(encoding="utf-8")
        post_iteration_qa = (ROOT / "docs" / "CODEX_TASKS" / "POST_ITERATION_QA.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = "\n".join([handoff_contract, post_iteration_qa, readme]).lower()

        self.assertIn("atomic", combined)
        self.assertIn("internal", combined)
        self.assertIn("external", combined)
        self.assertIn("archive/latest", combined)
        self.assertIn("validation provenance", combined)

    def test_atomic_latest_update_does_not_replace_previous_latest_on_failed_validation(self) -> None:
        good = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_good_latest",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )
        with zipfile.ZipFile(good.zip_path, "r") as archive:
            good_context = archive.read("HANDOFF_CONTEXT.md")
        latest_root = self.fixture / "repo"
        write_latest_handoff_files(good.zip_path, latest_root, good_context, good.sha256)
        latest_zip = latest_root / "outputs" / "handoffs" / "latest" / "HANDOFF_LATEST.zip"
        before_sha = sha256_file(latest_zip)

        bad = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_bad_latest",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )
        with zipfile.ZipFile(bad.zip_path, "r") as archive:
            bad_context = archive.read("HANDOFF_CONTEXT.md").replace(b"unit_bad_latest", b"stale_context")
        with self.assertRaisesRegex(ValueError, "context does not match"):
            write_latest_handoff_files(bad.zip_path, latest_root, bad_context, bad.sha256)

        self.assertEqual(sha256_file(latest_zip), before_sha)
        details = validate_latest_handoff(latest_zip.parent, archive_zip_path=good.zip_path)
        self.assertEqual(details["bundle_name"], "unit_good_latest")

    def test_upload_ready_trio_is_unique_and_matches_latest_and_archive(self) -> None:
        result = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_upload_ready",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )
        with zipfile.ZipFile(result.zip_path, "r") as archive:
            context = archive.read("HANDOFF_CONTEXT.md")
        repo_root = self.fixture / "upload_repo"
        write_latest_handoff_files(result.zip_path, repo_root, context, result.sha256)
        upload_dir = write_upload_ready_handoff_files(result.zip_path, repo_root, context, result.sha256)
        bundle_id = upload_bundle_id_from_context(context, result.sha256)
        upload_zip = upload_dir / f"{bundle_id}.zip"
        upload_context = upload_dir / f"{bundle_id}_CONTEXT.md"
        upload_sha = upload_dir / f"{bundle_id}.sha256"
        latest_zip = repo_root / "outputs" / "handoffs" / "latest" / "HANDOFF_LATEST.zip"

        self.assertTrue(upload_zip.exists())
        self.assertTrue(upload_context.exists())
        self.assertTrue(upload_sha.exists())
        self.assertIn("patch", bundle_id)
        self.assertIn("unit_upload_ready", bundle_id)
        self.assertIn(result.short_head, bundle_id)
        self.assertTrue(bundle_id.endswith(result.sha256[:8].upper()))
        self.assertEqual(sha256_file(upload_zip), sha256_file(latest_zip))
        self.assertEqual(upload_context.read_bytes(), context)
        self.assertIn(upload_zip.name, upload_sha.read_text(encoding="utf-8"))
        details = validate_upload_ready_handoff(upload_dir, archive_zip_path=result.zip_path)
        self.assertEqual(details["bundle_name"], "unit_upload_ready")

    def test_upload_ready_is_not_written_when_latest_archive_validation_fails(self) -> None:
        good = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_upload_good",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )
        with zipfile.ZipFile(good.zip_path, "r") as archive:
            good_context = archive.read("HANDOFF_CONTEXT.md")
        repo_root = self.fixture / "blocked_upload_repo"
        write_latest_handoff_files(good.zip_path, repo_root, good_context, good.sha256)

        bad = export_handoff_bundle(
            profile="patch",
            bundle_name="unit_upload_bad",
            repo_root=ROOT,
            output_dir=self.fixture,
            include_paths=[self.safe_file],
        )
        with zipfile.ZipFile(bad.zip_path, "r") as archive:
            bad_context = archive.read("HANDOFF_CONTEXT.md")
        bad_id = upload_bundle_id_from_context(bad_context, bad.sha256)

        with self.assertRaisesRegex(ValueError, "archive copy hash"):
            write_upload_ready_handoff_files(bad.zip_path, repo_root, bad_context, bad.sha256)

        self.assertFalse((repo_root / "outputs" / "handoffs" / "upload_ready" / bad_id).exists())


if __name__ == "__main__":
    unittest.main()
