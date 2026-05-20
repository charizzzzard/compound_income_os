import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from src.data_freshness import (
    build_data_freshness_summary,
    render_markdown,
    write_summary_json,
)


TMP = Path("tests/_tmp_data_freshness")


def write_config(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"contract_version": "v1-test", "items": items}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def base_item(data_class: str, source_path: Path | str, threshold_days: int = 7) -> dict:
    return {
        "data_class": data_class,
        "source_path": str(source_path),
        "freshness_date_fields": ["as_of_date", "data_date"],
        "threshold_days": threshold_days,
        "required": True,
        "missing_behavior": "MISSING",
        "unknown_behavior": "UNKNOWN",
        "review_on_stale": True,
        "review_on_missing": True,
        "review_on_unknown": True,
        "blocks_dashboard": True,
        "blocks_replay": True,
        "blocks_outcome_attribution": True,
    }


class DataFreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(TMP, ignore_errors=True)

    def test_fresh_and_stale_csv_items_are_explicit(self) -> None:
        fresh_csv = TMP / "fresh.csv"
        stale_csv = TMP / "stale.csv"
        fresh_csv.write_text("as_of_date\n2026-05-19\n", encoding="utf-8")
        stale_csv.write_text("as_of_date\n2026-04-01\n", encoding="utf-8")
        config = TMP / "config.json"
        write_config(
            config,
            [
                base_item("fresh_class", fresh_csv),
                base_item("stale_class", stale_csv),
            ],
        )

        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )
        by_class = {item["data_class"]: item for item in summary["items"]}

        self.assertEqual(by_class["fresh_class"]["freshness_status"], "FRESH")
        self.assertEqual(by_class["fresh_class"]["age_days"], 1)
        self.assertEqual(by_class["fresh_class"]["evidence_source"], "field:as_of_date")
        self.assertEqual(by_class["fresh_class"]["min_as_of_date"], "2026-05-19")
        self.assertEqual(by_class["fresh_class"]["max_as_of_date"], "2026-05-19")
        self.assertEqual(by_class["fresh_class"]["valid_date_count"], 1)
        self.assertEqual(by_class["fresh_class"]["record_count"], 1)
        self.assertEqual(by_class["stale_class"]["freshness_status"], "STALE")
        self.assertTrue(by_class["stale_class"]["review_required"])
        self.assertNotEqual(summary["overall_status"], "FRESH")

    def test_mixed_row_dates_use_oldest_date_and_become_stale(self) -> None:
        csv_path = TMP / "mixed.csv"
        csv_path.write_text("as_of_date,ticker\n2026-05-19,A\n2025-01-01,B\n", encoding="utf-8")
        config = TMP / "config.json"
        write_config(config, [base_item("mixed_class", csv_path)])

        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )
        item = summary["items"][0]

        self.assertEqual(item["freshness_status"], "STALE")
        self.assertEqual(item["as_of_date"], "2025-01-01")
        self.assertEqual(item["min_as_of_date"], "2025-01-01")
        self.assertEqual(item["max_as_of_date"], "2026-05-19")
        self.assertEqual(item["age_days"], 504)
        self.assertEqual(item["valid_date_count"], 2)
        self.assertEqual(item["record_count"], 2)
        self.assertTrue(item["review_required"])

    def test_future_row_date_requires_review(self) -> None:
        csv_path = TMP / "future_mixed.csv"
        csv_path.write_text("as_of_date,ticker\n2026-05-19,A\n2026-05-21,B\n", encoding="utf-8")
        config = TMP / "config.json"
        write_config(config, [base_item("future_mixed_class", csv_path)])

        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )
        item = summary["items"][0]

        self.assertEqual(item["freshness_status"], "REVIEW_REQUIRED")
        self.assertEqual(item["reason"], "SOURCE_DATE_AFTER_AS_OF")
        self.assertTrue(item["review_required"])
        self.assertEqual(item["min_as_of_date"], "2026-05-19")
        self.assertEqual(item["max_as_of_date"], "2026-05-21")

    def test_invalid_mixed_date_signal_is_not_fresh(self) -> None:
        csv_path = TMP / "invalid_mixed.csv"
        csv_path.write_text("as_of_date,ticker\n2026-05-19,A\nnot-a-date,B\n", encoding="utf-8")
        config = TMP / "config.json"
        write_config(config, [base_item("invalid_mixed_class", csv_path)])

        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )
        item = summary["items"][0]

        self.assertNotEqual(item["freshness_status"], "FRESH")
        self.assertEqual(item["freshness_status"], "REVIEW_REQUIRED")
        self.assertEqual(item["reason"], "INVALID_DATE_SIGNAL")
        self.assertTrue(item["review_required"])
        self.assertEqual(item["valid_date_count"], 1)
        self.assertEqual(item["invalid_date_count"], 1)

    def test_missing_artifact_is_not_fresh(self) -> None:
        config = TMP / "config.json"
        write_config(config, [base_item("missing_class", TMP / "missing.csv")])

        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )
        item = summary["items"][0]

        self.assertEqual(item["freshness_status"], "MISSING")
        self.assertEqual(item["reason"], "ARTIFACT_MISSING")
        self.assertTrue(item["review_required"])
        self.assertTrue(summary["review_required"])

    def test_unknown_artifact_with_no_date_signal_is_not_fresh(self) -> None:
        csv_path = TMP / "unknown.csv"
        csv_path.write_text("symbol,value\nMSFT,1\n", encoding="utf-8")
        config = TMP / "config.json"
        write_config(config, [base_item("unknown_class", csv_path)])

        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )
        item = summary["items"][0]

        self.assertEqual(item["freshness_status"], "UNKNOWN")
        self.assertEqual(item["reason"], "NO_DATE_SIGNAL")
        self.assertTrue(item["review_required"])
        self.assertEqual(item["record_count"], 1)
        self.assertEqual(item["valid_date_count"], 0)

    def test_no_date_signal_remains_unknown(self) -> None:
        csv_path = TMP / "no_dates.csv"
        csv_path.write_text("symbol,value\nMSFT,1\nAAPL,2\n", encoding="utf-8")
        config = TMP / "config.json"
        write_config(config, [base_item("no_dates_class", csv_path)])

        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )
        item = summary["items"][0]

        self.assertEqual(item["freshness_status"], "UNKNOWN")
        self.assertEqual(item["reason"], "NO_DATE_SIGNAL")
        self.assertEqual(item["record_count"], 2)
        self.assertEqual(item["missing_date_count"], 2)

    def test_json_object_single_date_still_fresh(self) -> None:
        json_path = TMP / "state.json"
        json_path.write_text(
            json.dumps({"as_of_date": "2026-05-20", "status": "PASS"}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        config = TMP / "config.json"
        write_config(config, [base_item("json_class", json_path)])

        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )

        self.assertEqual(summary["items"][0]["freshness_status"], "FRESH")
        self.assertEqual(summary["items"][0]["min_as_of_date"], "2026-05-20")
        self.assertEqual(summary["items"][0]["max_as_of_date"], "2026-05-20")
        self.assertFalse(summary["review_required"])
        self.assertEqual(summary["overall_status"], "FRESH")

    def test_future_date_requires_review(self) -> None:
        csv_path = TMP / "future.csv"
        csv_path.write_text("as_of_date\n2026-05-21\n", encoding="utf-8")
        config = TMP / "config.json"
        write_config(config, [base_item("future_class", csv_path)])

        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )
        item = summary["items"][0]

        self.assertEqual(item["freshness_status"], "REVIEW_REQUIRED")
        self.assertEqual(item["reason"], "SOURCE_DATE_AFTER_AS_OF")
        self.assertEqual(summary["overall_status"], "REVIEW_REQUIRED")

    def test_external_absolute_path_is_redacted(self) -> None:
        config = TMP / "config.json"
        write_config(config, [base_item("private_path", r"C:\Users\Max\private.csv")])

        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )
        text = json.dumps(summary, sort_keys=True)

        self.assertIn("EXTERNAL_PATH_REDACTED:private_path", text)
        self.assertNotIn(r"C:\Users\Max", text)
        self.assertEqual(summary["items"][0]["freshness_status"], "REVIEW_REQUIRED")

    def test_bad_config_fails_fast(self) -> None:
        config = TMP / "config.json"
        write_config(config, [base_item("bad_class", TMP / "x.csv") | {"threshold_days": -1}])

        with self.assertRaises(ValueError):
            build_data_freshness_summary(config_path=config, as_of_date="2026-05-20")

    def test_json_serialization_is_deterministic(self) -> None:
        csv_path = TMP / "fresh.csv"
        csv_path.write_text("as_of_date\n2026-05-20\n", encoding="utf-8")
        config = TMP / "config.json"
        out_json = TMP / "summary.json"
        write_config(config, [base_item("fresh_class", csv_path)])
        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )

        write_summary_json(summary, out_json)
        parsed = json.loads(out_json.read_text(encoding="utf-8"))

        self.assertEqual(parsed["overall_status"], "FRESH")
        self.assertIn('\n  "contract_version"', out_json.read_text(encoding="utf-8"))
        self.assertIs(parsed["review_required"], False)
        self.assertIsInstance(parsed["items"], list)

    def test_markdown_contains_non_scope_and_no_recommendation(self) -> None:
        csv_path = TMP / "fresh.csv"
        csv_path.write_text("as_of_date\n2026-05-20\n", encoding="utf-8")
        config = TMP / "config.json"
        write_config(config, [base_item("fresh_class", csv_path)])
        summary = build_data_freshness_summary(
            config_path=config,
            as_of_date="2026-05-20",
            generated_at_utc="2026-05-20T00:00:00Z",
        )

        markdown = render_markdown(summary)

        self.assertIn("no broker/order/trading", markdown)
        self.assertNotIn("buy signal", markdown.lower())
        self.assertNotIn("sell signal", markdown.lower())
        self.assertNotIn("order signal", markdown.lower())

    def test_cli_writes_outputs_to_configured_temp_paths(self) -> None:
        csv_path = TMP / "fresh.csv"
        csv_path.write_text("as_of_date\n2026-05-20\n", encoding="utf-8")
        config = TMP / "config.json"
        out_json = TMP / "out.json"
        report = TMP / "out.md"
        write_config(config, [base_item("fresh_class", csv_path)])

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.data_freshness",
                "--config",
                str(config),
                "--as-of-date",
                "2026-05-20",
                "--out-json",
                str(out_json),
                "--report",
                str(report),
            ],
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(out_json.exists())
        self.assertTrue(report.exists())
        self.assertEqual(json.loads(out_json.read_text(encoding="utf-8"))["overall_status"], "FRESH")


if __name__ == "__main__":
    unittest.main()
