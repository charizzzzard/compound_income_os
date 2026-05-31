from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

from src.monthly_portfolio_decision_brief import (
    CSV_FIELDS,
    build_monthly_portfolio_decision_brief,
    run_monthly_portfolio_decision_brief,
)

CONTRACT_PATH = Path("docs/contracts/MONTHLY_PORTFOLIO_DECISION_BRIEF_CONTRACT.md")


def _clean_test_dir(name: str) -> Path:
    path = Path("outputs") / "test_tmp" / name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True)
    return path


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _ranking_rows() -> list[dict[str, str]]:
    return [
        {
            "rank": "1",
            "ticker": "AAA",
            "target_action": "DO_NOT_BUY",
            "allocation_status": "NOT_ELIGIBLE",
            "suggested_buy_amount_eur": "0",
            "rationale": "upstream rationale one",
            "constraint_checks": "missing_data=REVIEW",
            "valuation_comment": "REVIEW",
            "mandate_fit_comment": "Synthetic fixture.",
            "execution_mode": "SAVINGS_PLAN_EXISTING",
            "execution_mode_reason": "upstream_route_preserved",
        },
        {
            "rank": "2",
            "ticker": "BBB",
            "target_action": "HOLD_CASH",
            "allocation_status": "SELECTED_THIS_MONTH",
            "suggested_buy_amount_eur": "100",
            "rationale": "upstream rationale two",
            "constraint_checks": "portfolio_rule=hold_cash_allowed",
            "valuation_comment": "Cash.",
            "mandate_fit_comment": "Synthetic fixture.",
            "execution_mode": "",
            "execution_mode_reason": "not_a_buy_candidate",
        },
    ]


def _fixture_paths(prefix: str) -> dict[str, Path]:
    root = _clean_test_dir(prefix)
    return {
        "root": root,
        "ranking": root / "ranking.csv",
        "cash": root / "cash.csv",
        "rebalance": root / "rebalance.csv",
        "freshness": root / "freshness.json",
        "decision_quality": root / "decision_quality.json",
        "queue": root / "queue.csv",
        "out_json": root / "brief.json",
        "out_csv": root / "brief.csv",
        "report": root / "brief.md",
    }


def _write_complete_inputs(paths: dict[str, Path]) -> None:
    _write_csv(paths["ranking"], list(_ranking_rows()[0]), _ranking_rows())
    _write_csv(
        paths["cash"],
        ["status", "trigger", "data_quality_flag"],
        [{"status": "CASH_REFILL_NOT_REQUIRED", "trigger": "NONE", "data_quality_flag": "OK"}],
    )
    _write_csv(
        paths["rebalance"],
        ["bucket", "band_status", "recommended_action", "data_quality_flag"],
        [{"bucket": "CASH", "band_status": "WITHIN_BAND", "recommended_action": "HOLD", "data_quality_flag": "OK"}],
    )
    _write_json(
        paths["freshness"],
        {
            "overall_status": "FRESH",
            "review_required": False,
            "summary_counts": {
                "FRESH": 1,
                "MISSING": 0,
                "NOT_APPLICABLE": 0,
                "REVIEW_REQUIRED": 0,
                "STALE": 0,
                "UNKNOWN": 0,
            },
        },
    )
    _write_json(
        paths["decision_quality"],
        {
            "decision_confidence_level": "MEDIUM",
            "review_required": False,
            "review_reason_codes": [],
        },
    )
    _write_csv(paths["queue"], ["queue_id", "priority", "reason_codes"], [])


def _run_with_paths(paths: dict[str, Path]) -> dict[str, object]:
    result = run_monthly_portfolio_decision_brief(
        as_of_date="2026-05-30",
        generated_at_utc="2026-05-30T00:00:00Z",
        monthly_ranking=paths["ranking"],
        cash_refill=paths["cash"],
        rebalance=paths["rebalance"],
        data_freshness=paths["freshness"],
        decision_quality=paths["decision_quality"],
        decision_review_queue=paths["queue"],
        out_json=paths["out_json"],
        out_csv=paths["out_csv"],
        report=paths["report"],
    )
    return result.brief


def test_deterministic_json_csv_and_markdown_outputs() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_deterministic")
    try:
        _write_complete_inputs(paths)
        _run_with_paths(paths)
        first_json = paths["out_json"].read_bytes()
        first_csv = paths["out_csv"].read_bytes()
        first_report = paths["report"].read_bytes()
        _run_with_paths(paths)

        assert paths["out_json"].read_bytes() == first_json
        assert paths["out_csv"].read_bytes() == first_csv
        assert paths["report"].read_bytes() == first_report
        assert list(csv.DictReader(paths["out_csv"].read_text(encoding="utf-8").splitlines()))[0].keys() == set(CSV_FIELDS)
        parsed = json.loads(paths["out_json"].read_text(encoding="utf-8"))
        assert parsed["decision_brief_status"] == "READY"
        assert parsed["generated_at_utc"] == "2026-05-30T00:00:00Z"
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_missing_mandatory_ranking_blocks_not_ready() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_missing_ranking")
    try:
        _write_complete_inputs(paths)
        paths["ranking"].unlink()

        brief = _run_with_paths(paths)

        assert brief["decision_brief_status"] == "BLOCKED"
        artifact = next(item for item in brief["input_artifact_status"] if item["label"] == "monthly_ranking")
        assert artifact["status"] == "MISSING"
        assert "READY" not in json.dumps(brief["portfolio_decision_readiness"], sort_keys=True)
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_top_ranking_rows_are_preserved_not_recalculated() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_ranking")
    try:
        _write_complete_inputs(paths)

        brief = _run_with_paths(paths)

        top_rows = brief["ranking_summary"]["top_rows"]
        assert top_rows[0]["ticker"] == "AAA"
        assert top_rows[0]["target_action"] == "DO_NOT_BUY"
        assert top_rows[0]["suggested_buy_amount_eur"] == "0"
        assert top_rows[0]["rationale"] == "upstream rationale one"
        assert top_rows[0]["execution_mode"] == "SAVINGS_PLAN_EXISTING"
        assert top_rows[0]["execution_mode_reason"] == "upstream_route_preserved"
        assert top_rows[1]["ticker"] == "BBB"
        csv_rows = list(csv.DictReader(paths["out_csv"].read_text(encoding="utf-8").splitlines()))
        routing_row = next(row for row in csv_rows if row["item"] == "1.execution_mode")
        assert routing_row["status"] == "SAVINGS_PLAN_EXISTING"
        assert routing_row["notes"] == "upstream_route_preserved"
        report = paths["report"].read_text(encoding="utf-8")
        assert "`SAVINGS_PLAN_EXISTING`" in report
        assert "`upstream_route_preserved`" in report
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_missing_routing_fields_do_not_infer_or_break_brief() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_missing_routing_fields")
    try:
        _write_complete_inputs(paths)
        rows = [
            {
                key: value
                for key, value in row.items()
                if key not in {"execution_mode", "execution_mode_reason"}
            }
            for row in _ranking_rows()
        ]
        _write_csv(paths["ranking"], list(rows[0]), rows)

        brief = _run_with_paths(paths)

        top_rows = brief["ranking_summary"]["top_rows"]
        assert brief["decision_brief_status"] == "READY"
        assert top_rows[0]["execution_mode"] == ""
        assert top_rows[0]["execution_mode_reason"] == ""
        assert "SAVINGS_PLAN_EXISTING" not in json.dumps(brief, sort_keys=True)
        assert "upstream_route_preserved" not in json.dumps(brief, sort_keys=True)

        csv_rows = list(csv.DictReader(paths["out_csv"].read_text(encoding="utf-8").splitlines()))
        assert not any(row["item"].endswith(".execution_mode") for row in csv_rows)
        assert not any(row["status"] == "SAVINGS_PLAN_EXISTING" for row in csv_rows)
        assert not any(row["notes"] == "upstream_route_preserved" for row in csv_rows)

        report = paths["report"].read_text(encoding="utf-8")
        assert (
            "| 1 | `AAA` | `DO_NOT_BUY` | `NOT_ELIGIBLE` | 0 | `NOT_AVAILABLE` | "
            "`NOT_AVAILABLE` | upstream rationale one |"
        ) in report
        assert "`SAVINGS_PLAN_EXISTING`" not in report
        assert "`upstream_route_preserved`" not in report
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_data_freshness_decision_quality_and_portfolio_health_missing_remain_visible() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_missing_states")
    try:
        _write_complete_inputs(paths)
        paths["freshness"].unlink()
        paths["decision_quality"].unlink()
        paths["cash"].unlink()

        brief = _run_with_paths(paths)

        assert brief["decision_brief_status"] == "REVIEW"
        assert brief["data_freshness_summary"]["overall_status"] == "NOT_AVAILABLE"
        assert brief["decision_quality_summary"]["decision_confidence_level"] == "NOT_AVAILABLE"
        assert brief["portfolio_health_summary"]["cash_refill_artifact_status"] == "MISSING"
        report = paths["report"].read_text(encoding="utf-8")
        assert "NOT_AVAILABLE" in report
        assert "MISSING" in report
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_degraded_data_freshness_remains_visible_and_reviews() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_degraded_freshness")
    try:
        _write_complete_inputs(paths)
        _write_json(
            paths["freshness"],
            {
                "overall_status": "REVIEW_REQUIRED",
                "review_required": True,
                "summary_counts": {
                    "FRESH": 0,
                    "MISSING": 1,
                    "NOT_APPLICABLE": 1,
                    "REVIEW_REQUIRED": 1,
                    "STALE": 1,
                    "UNKNOWN": 1,
                },
            },
        )

        brief = _run_with_paths(paths)

        assert brief["decision_brief_status"] == "REVIEW"
        assert brief["data_freshness_summary"]["summary_counts"]["STALE"] == 1
        assert brief["data_freshness_summary"]["summary_counts"]["MISSING"] == 1
        assert brief["data_freshness_summary"]["summary_counts"]["UNKNOWN"] == 1
        assert brief["data_freshness_summary"]["summary_counts"]["REVIEW_REQUIRED"] == 1
        assert brief["data_freshness_summary"]["summary_counts"]["NOT_APPLICABLE"] == 1
        assert set(brief["data_freshness_summary"]["degraded_state_indicators"]) == {
            "STALE",
            "MISSING",
            "UNKNOWN",
            "REVIEW_REQUIRED",
        }
        csv_rows = list(csv.DictReader(paths["out_csv"].read_text(encoding="utf-8").splitlines()))
        freshness_count_rows = [row for row in csv_rows if row["section"] == "data_freshness_summary_counts"]
        counts_by_status = {row["item"]: row["value"] for row in freshness_count_rows}
        assert counts_by_status == {
            "FRESH": "0",
            "MISSING": "1",
            "NOT_APPLICABLE": "1",
            "REVIEW_REQUIRED": "1",
            "STALE": "1",
            "UNKNOWN": "1",
        }
        report = paths["report"].read_text(encoding="utf-8")
        assert "| `NOT_APPLICABLE` | 1 |" in report
        assert "| `REVIEW_REQUIRED` | 1 |" in report
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_outputs_do_not_leak_local_absolute_or_private_paths() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_path_redaction")
    try:
        _write_complete_inputs(paths)
        brief = build_monthly_portfolio_decision_brief(
            as_of_date="2026-05-30",
            monthly_ranking=paths["ranking"],
            data_freshness="data/raw/private/secret.csv",
            decision_quality=r"C:\Users\Operator\private_decision_quality.json",
        )
        text = json.dumps(brief, sort_keys=True)

        assert "data/raw/private/secret.csv" not in text
        assert "C:\\Users\\Operator" not in text
        assert "EXTERNAL_PATH_REDACTED:data_freshness_summary" in text
        assert "EXTERNAL_PATH_REDACTED:decision_quality_state" in text
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_foreign_windows_absolute_path_is_redacted_cross_platform() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_windows_path")
    try:
        _write_complete_inputs(paths)

        brief = build_monthly_portfolio_decision_brief(
            as_of_date="2026-05-30",
            monthly_ranking=paths["ranking"],
            decision_quality=r"C:\Users\Operator\private_decision_quality.json",
        )
        text = json.dumps(brief, sort_keys=True)

        assert r"C:\Users\Operator\private_decision_quality.json" not in text
        assert "EXTERNAL_PATH_REDACTED:decision_quality_state" in text
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_foreign_unc_path_is_redacted_cross_platform() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_unc_path")
    try:
        _write_complete_inputs(paths)

        brief = build_monthly_portfolio_decision_brief(
            as_of_date="2026-05-30",
            monthly_ranking=paths["ranking"],
            decision_quality=r"\\server\share\private.json",
        )
        text = json.dumps(brief, sort_keys=True)

        assert r"\\server\share\private.json" not in text
        assert "EXTERNAL_PATH_REDACTED:decision_quality_state" in text
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_markdown_contains_explicit_non_claims() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_non_claims")
    try:
        _write_complete_inputs(paths)

        _run_with_paths(paths)

        report = paths["report"].read_text(encoding="utf-8")
        for phrase in (
            "no order execution",
            "no buy/sell automation",
            "no investment advice",
            "no valuation automation",
            "no scoring formula change",
            "no ranking formula change",
            "no broker/provider/API integration",
            "no replay/backtesting/outcome attribution",
        ):
            assert phrase in report
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_json_top_level_keys_and_csv_headers_are_stable() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_schema")
    try:
        _write_complete_inputs(paths)

        _run_with_paths(paths)

        parsed = json.loads(paths["out_json"].read_text(encoding="utf-8"))
        assert list(parsed) == sorted(parsed)
        with paths["out_csv"].open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames == CSV_FIELDS
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_cli_works_with_explicit_outputs() -> None:
    paths = _fixture_paths("_tmp_monthly_brief_cli")
    try:
        _write_complete_inputs(paths)
        command = [
            sys.executable,
            "-m",
            "src.monthly_portfolio_decision_brief",
            "--as-of-date",
            "2026-05-30",
            "--generated-at-utc",
            "2026-05-30T00:00:00Z",
            "--monthly-ranking",
            str(paths["ranking"]),
            "--cash-refill",
            str(paths["cash"]),
            "--rebalance",
            str(paths["rebalance"]),
            "--data-freshness",
            str(paths["freshness"]),
            "--decision-quality",
            str(paths["decision_quality"]),
            "--decision-review-queue",
            str(paths["queue"]),
            "--out-json",
            str(paths["out_json"]),
            "--out-csv",
            str(paths["out_csv"]),
            "--report",
            str(paths["report"]),
        ]

        completed = subprocess.run(command, text=True, capture_output=True, check=False)

        assert completed.returncode == 0, completed.stderr
        assert "decision_brief_status=READY" in completed.stdout
        assert paths["out_json"].exists()
        assert paths["out_csv"].exists()
        assert paths["report"].exists()
    finally:
        shutil.rmtree(paths["root"], ignore_errors=True)


def test_contract_documents_generated_boundary_and_non_claims() -> None:
    text = CONTRACT_PATH.read_text(encoding="utf-8")

    assert "data/processed/monthly_portfolio_decision_brief.json" in text
    assert "reports/<as_of_date>/monthly_portfolio_decision_brief.md" in text
    assert "generated local artifacts by default" in text
    assert "must not be committed" in text
    assert "Missing, stale or unknown evidence must remain visible." in text
    for phrase in (
        "order execution",
        "buy/sell automation",
        "investment advice",
        "valuation automation",
        "scoring formula changes",
        "ranking formula changes",
        "portfolio-rule changes",
        "production readiness",
        "investment readiness",
    ):
        assert phrase in text
