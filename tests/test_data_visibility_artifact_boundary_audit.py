from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from src.data_visibility_artifact_boundary_audit import (
    FIELDNAMES,
    build_audit_rows,
    run_audit,
)


def rows_by_path() -> dict[str, dict[str, str]]:
    return {row.path: row.__dict__ for row in build_audit_rows()}


def test_private_raw_paths_are_private_or_not_repo_material() -> None:
    rows = rows_by_path()

    for path in [
        "data/raw/private/example.csv",
        "data/raw/private/fundamentals/personal_fundamentals_snapshot.csv",
        "data/raw/private/fundamentals/personal_fundamentals_snapshot_review.csv",
    ]:
        row = rows[path]
        assert row["repo_tracking_intent"] in {"PRIVATE_LOCAL_ONLY", "SHOULD_NOT_EXIST_IN_REPO"}
        assert row["privacy_risk_if_tracked"] == "CRITICAL"
        assert row["project_level_impact"] == "PRIVACY_PROTECTION"
        assert row["recommended_action"] == "KEEP_IGNORED"


def test_personal_raw_paths_are_not_broadly_trackable_except_templates() -> None:
    rows = rows_by_path()

    assert rows["data/raw/personal_positions_snapshot.csv"]["repo_tracking_intent"] == "PRIVATE_LOCAL_ONLY"
    assert rows["data/raw/personal_fundamentals_master.csv"]["repo_tracking_intent"] == "PRIVATE_LOCAL_ONLY"
    assert rows["data/raw/personal_fundamentals_master_template.csv"]["repo_tracking_intent"] == "TRACKED_TEMPLATE"
    assert rows["data/raw/personal_sec_identity_map_template.csv"]["repo_tracking_intent"] == "TRACKED_TEMPLATE"


def test_generated_processed_artifacts_remain_local_only() -> None:
    rows = rows_by_path()

    for path in [
        "data/processed/personal_monthly_buy_ranking.csv",
        "data/processed/rebalance_proposals.csv",
        "data/processed/decision_quality_state.json",
        "data/processed/data_freshness_summary.json",
    ]:
        row = rows[path]
        assert row["repo_tracking_intent"] == "GENERATED_LOCAL_ONLY"
        assert row["recommended_action"] == "ADD_MANIFEST_OR_HASH_ONLY"


def test_personal_reports_remain_generated_or_private_local_only() -> None:
    rows = rows_by_path()

    for path in [
        "reports/2026-05-30/personal_run_report.md",
        "reports/2026-05-30/personal_monthly_decision_report.md",
    ]:
        row = rows[path]
        assert row["repo_tracking_intent"] in {"GENERATED_LOCAL_ONLY", "PRIVATE_LOCAL_ONLY"}
        assert row["privacy_risk_if_tracked"] in {"HIGH", "MEDIUM"}


def test_future_monthly_decision_brief_requires_boundary_decision() -> None:
    rows = rows_by_path()

    for path in [
        "data/processed/monthly_portfolio_decision_brief.json",
        "data/processed/monthly_portfolio_decision_brief.csv",
        "reports/2026-05-30/monthly_portfolio_decision_brief.md",
    ]:
        row = rows[path]
        assert row["project_level_impact"] == "FUTURE_PATCH_PRECONDITION"
        assert row["decision_risk_if_ignored"] == "HIGH"
        assert row["recommended_action"] == "ADD_DOC_BOUNDARY"
        assert "Future operational decision artifact" in row["notes"]


def test_future_ranking_robustness_is_review_relevant_not_auto_commit_safe() -> None:
    rows = rows_by_path()

    for path in [
        "data/processed/ranking_robustness_sensitivity.json",
        "data/processed/ranking_robustness_sensitivity.csv",
        "reports/2026-05-30/ranking_robustness_sensitivity_report.md",
    ]:
        row = rows[path]
        assert row["project_level_impact"] == "FUTURE_PATCH_PRECONDITION"
        assert row["decision_risk_if_ignored"] == "MEDIUM"
        assert row["recommended_action"] == "ADD_DOC_BOUNDARY"
        assert "not automatically safe to commit" in row["notes"]


def test_external_review_packet_metadata_and_zip_are_classified_separately() -> None:
    rows = rows_by_path()

    assert rows["external_review_packet/HANDOFF_LATEST_CONTEXT.md"]["handoff_visibility"] == "REVIEW_PACKET_METADATA"
    assert rows["external_review_packet/HANDOFF_LATEST.sha256"]["repo_tracking_intent"] == "REVIEW_PACKET_ONLY"
    zip_row = rows["external_review_packet/HANDOFF_LATEST.zip"]
    assert zip_row["repo_tracking_intent"] == "REVIEW_PACKET_ONLY"
    assert zip_row["handoff_visibility"] == "REVIEW_PACKET_METADATA"


def test_outputs_remain_local_generated_evidence_not_authoritative_handoff() -> None:
    rows = rows_by_path()

    for path in [
        "outputs/handoffs/latest/HANDOFF_LATEST.zip",
        "outputs/handoffs/latest/HANDOFF_LATEST.sha256",
        "outputs/reports/local_validation.log",
    ]:
        row = rows[path]
        assert row["repo_tracking_intent"] in {"GENERATED_LOCAL_ONLY", "SHOULD_NOT_EXIST_IN_REPO"}
        assert row["project_level_impact"] == "SOURCE_OF_TRUTH_AMBIGUITY"


def test_strategy_private_and_templates_have_distinct_boundaries() -> None:
    rows = rows_by_path()

    assert rows["strategy/private/current_strategy.md"]["repo_tracking_intent"] == "PRIVATE_LOCAL_ONLY"
    assert rows["strategy/private/current_strategy.md"]["privacy_risk_if_tracked"] == "CRITICAL"
    assert rows["strategy/templates/example_strategy.md"]["repo_tracking_intent"] == "TRACKED_TEMPLATE"
    assert rows["strategy/templates/example_strategy.md"]["recommended_action"] == "TRACK_TEMPLATE_ONLY"


def test_forbidden_paths_are_not_recommended_for_tracking() -> None:
    rows = rows_by_path()

    for path in [
        ".env",
        ".env.local",
        "website/app/.env.local",
        "sec_user_agent.local.txt",
        "node_modules/example.js",
        "website/compound-income-os-landing/dist/index.html",
        "outputs/reports/local_validation.log",
        "__pycache__/example.pyc",
    ]:
        row = rows[path]
        assert row["recommended_action"] in {"KEEP_IGNORED", "ADD_TO_OMITTED_ARTIFACT_REGISTER"}
        assert row["privacy_risk_if_tracked"] in {"CRITICAL", "MEDIUM", "NONE"}


def test_no_private_files_required_or_local_absolute_paths_emitted() -> None:
    tmp_path = _clean_test_dir("tests/_tmp_data_visibility_paths")
    try:
        csv_path = tmp_path / "audit.csv"
        json_path = tmp_path / "audit.json"
        report_path = tmp_path / "audit.md"

        run_audit(as_of_date="2026-05-30", out_csv=csv_path, out_json=json_path, report=report_path)

        combined = csv_path.read_text(encoding="utf-8") + json_path.read_text(encoding="utf-8") + report_path.read_text(encoding="utf-8")
        assert "C:\\Users\\" not in combined
        assert "/home/" not in combined
        assert "/Users/" not in combined
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_outputs_are_deterministic_and_complete() -> None:
    tmp_path = _clean_test_dir("tests/_tmp_data_visibility_determinism")
    try:
        first = tmp_path / "first"
        second = tmp_path / "second"
        first.mkdir()
        second.mkdir()

        run_audit(
            as_of_date="2026-05-30",
            out_csv=first / "audit.csv",
            out_json=first / "audit.json",
            report=first / "audit.md",
        )
        run_audit(
            as_of_date="2026-05-30",
            out_csv=second / "audit.csv",
            out_json=second / "audit.json",
            report=second / "audit.md",
        )

        assert (first / "audit.csv").read_bytes() == (second / "audit.csv").read_bytes()
        assert (first / "audit.json").read_bytes() == (second / "audit.json").read_bytes()
        assert (first / "audit.md").read_bytes() == (second / "audit.md").read_bytes()

        csv_rows = list(csv.DictReader((first / "audit.csv").read_text(encoding="utf-8").splitlines()))
        json_rows = json.loads((first / "audit.json").read_text(encoding="utf-8"))
        assert list(csv_rows[0]) == FIELDNAMES
        assert len(csv_rows) == len(json_rows)
        for row in csv_rows:
            assert row["project_level_impact"]
            assert row["recommended_action"]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_data_source_registry_relations_are_visible() -> None:
    rows = rows_by_path()

    assert rows["data/raw/personal_fundamentals_master.csv"]["data_source_registry_relation"] == "CONFIGURED_REQUIRED"
    assert rows["data/raw/sample_watchlist.csv"]["data_source_registry_relation"] == "CONFIGURED_OPTIONAL"
    assert rows["data/raw/private/fundamentals/personal_fundamentals_snapshot.csv"]["data_source_registry_relation"] == "CONFIGURED_DISABLED"
    assert rows["data/processed/data_freshness_summary.json"]["data_source_registry_relation"] == "PRODUCED_OUTPUT"


def _clean_test_dir(path_value: str) -> Path:
    path = Path(path_value)
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True)
    return path
