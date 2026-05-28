from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import src.valuation_scoring_semantic_decision_quality_review as semantic
from src.valuation_scoring_semantic_decision_quality_review import run_valuation_scoring_semantic_decision_quality_review

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "docs" / "contracts" / "VALUATION_SCORING_SEMANTIC_DECISION_QUALITY_CONTRACT.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ValuationScoringSemanticDecisionQualityReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = ROOT / "tests" / "_tmp_valuation_scoring_semantic_review"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.csv_output = self.tmp / "review.csv"
        self.json_output = self.tmp / "review.json"
        self.report_output = self.tmp / "review.md"

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def write_artifact(self, relative_path: str, text: str) -> None:
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_review(self, artifacts: list[str]):
        return run_valuation_scoring_semantic_decision_quality_review(
            as_of_date="2026-05-21",
            repo_root=self.repo,
            artifacts=artifacts,
            output_csv=str(self.csv_output),
            output_json=str(self.json_output),
            report_output=str(self.report_output),
        )

    def test_cli_generates_csv_json_and_markdown_with_explicit_as_of_date(self) -> None:
        self.write_artifact(
            "src/scoring_engine.py",
            "purchase_state = 'BUYABLE'\neligible_for_purchase = True\n# REVIEW state remains visible\n",
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.valuation_scoring_semantic_decision_quality_review",
                "--as-of-date",
                "2026-05-21",
                "--repo-root",
                str(self.repo),
                "--artifact",
                "src/scoring_engine.py",
                "--output-csv",
                str(self.csv_output),
                "--output-json",
                str(self.json_output),
                "--report-output",
                str(self.report_output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.csv_output.exists())
        self.assertTrue(self.json_output.exists())
        self.assertTrue(self.report_output.exists())
        self.assertIn("checks_total=", result.stdout)
        self.assertIn("2026-05-21", self.report_output.read_text(encoding="utf-8"))

    def test_default_report_path_uses_as_of_date_not_wall_clock(self) -> None:
        self.assertEqual(
            semantic.default_report_output("2026-05-21"),
            "reports/2026-05-21/valuation_scoring_semantic_decision_quality_review.md",
        )

    def test_detects_buyable_and_eligible_for_purchase_surfaces(self) -> None:
        self.write_artifact("src/scoring_engine.py", "purchase_state = 'BUYABLE'\neligible_for_purchase = True\nREVIEW\n")
        self.run_review(["src/scoring_engine.py"])

        terms = {row["reviewed_term"]: row for row in read_csv(self.csv_output)}
        self.assertEqual(terms["BUYABLE"]["status"], "REVIEW")
        self.assertEqual(terms["eligible_for_purchase"]["semantic_category"], "AUTOMATION_RISK")

    def test_detects_fair_value_and_margin_certainty_risk_surfaces(self) -> None:
        self.write_artifact(
            "src/valuation_engine.py",
            "fair_value_estimate = 100\nmargin_of_safety_pct = 10\nfair_value_score = 70\nMISSING_DATA\n",
        )
        self.run_review(["src/valuation_engine.py"])

        terms = {row["reviewed_term"]: row for row in read_csv(self.csv_output)}
        self.assertEqual(terms["fair_value_estimate"]["semantic_category"], "CERTAINTY_RISK")
        self.assertEqual(terms["margin_of_safety_pct"]["status"], "WARNING")
        self.assertEqual(terms["fair_value_score"]["severity"], "P2")

    def test_missing_stale_conflict_masking_risk_is_visible(self) -> None:
        self.write_artifact("src/valuation_engine.py", "fair_value_estimate = 100\n")
        self.run_review(["src/valuation_engine.py"])

        rows = read_csv(self.csv_output)
        visibility = [row for row in rows if row["check_id"].startswith("FAILURE_MODE_VISIBILITY::")][0]
        self.assertEqual(visibility["status"], "REVIEW")
        self.assertIn("without visible missing/review/stale/conflict", visibility["risk_description"])

    def test_safe_bounded_wording_can_be_ok_or_info(self) -> None:
        self.write_artifact("src/personal_decision_quality_state.py", "review_required = True\nREVIEW\n")
        self.run_review(["src/personal_decision_quality_state.py"])

        rows = read_csv(self.csv_output)
        review_row = [row for row in rows if row["reviewed_term"] == "review_required"][0]
        visibility = [row for row in rows if row["check_id"].startswith("FAILURE_MODE_VISIBILITY::")][0]
        self.assertEqual(review_row["status"], "OK")
        self.assertEqual(visibility["status"], "OK")

    def test_risky_action_wording_is_fail(self) -> None:
        self.write_artifact(
            "reports/sample.md",
            "\n".join(
                [
                    "buy now",
                    "must buy",
                    "guaranteed",
                    "risk-free",
                    "automatically buy",
                    "execute order",
                ]
            ),
        )
        self.run_review(["reports/sample.md"])

        rows = read_csv(self.csv_output)
        fail_terms = [row["reviewed_term"] for row in rows if row["status"] == "FAIL" and row["severity"] == "P0"]
        self.assertGreaterEqual(len(fail_terms), 6)

    def test_malformed_numeric_surfaces_are_review_findings(self) -> None:
        self.write_artifact(
            "data/synthetic_valuation_surface.txt",
            "fair_value_estimate='12.5%'\npe_current='N/A'\nev_ebit_current='--'\nnormalized='not-a-number'\nmargin='12,5'\n",
        )
        self.run_review(["data/synthetic_valuation_surface.txt"])

        rows = read_csv(self.csv_output)
        malformed = [row for row in rows if row["check_id"].startswith("MALFORMED_NUMERIC_SURFACE::")]
        self.assertGreaterEqual(len(malformed), 5)
        self.assertTrue(all(row["status"] == "REVIEW" for row in malformed))
        self.assertTrue(all(row["semantic_category"] == "DATA_QUALITY_MASKING" for row in malformed))

    def test_failure_mode_terms_are_visible_even_without_other_review_terms(self) -> None:
        self.write_artifact(
            "reports/failure_modes.md",
            "BLOCKED\nREVIEW\nMISSING_DATA\nSTALE\nCONFLICT\nUNKNOWN\nINVALID\n",
        )
        self.run_review(["reports/failure_modes.md"])

        rows = read_csv(self.csv_output)
        failure_rows = [row for row in rows if row["check_id"].startswith("FAILURE_MODE_TERM::")]
        found_terms = {row["reviewed_term"] for row in failure_rows}
        self.assertTrue({"BLOCKED", "REVIEW", "MISSING_DATA", "STALE", "CONFLICT", "UNKNOWN", "INVALID"}.issubset(found_terms))
        self.assertTrue(all(row["semantic_category"] == "FAILURE_MODE_VISIBILITY" for row in failure_rows))
        self.assertTrue(any(row["status"] in {"WARNING", "OK"} for row in failure_rows))

    def test_generated_artifacts_preserve_non_scope_boundary_language(self) -> None:
        self.write_artifact("src/scoring_engine.py", "purchase_state = 'BUYABLE'\nREVIEW\n")
        self.run_review(["src/scoring_engine.py"])

        json_text = self.json_output.read_text(encoding="utf-8")
        report_text = self.report_output.read_text(encoding="utf-8")
        for phrase in [
            "read-only evidence",
            "no valuation automation",
            "no formula change",
            "no ranking change",
            "no buy/sell automation",
            "no investment advice",
            "Human Operator remains final authority",
        ]:
            self.assertIn(phrase, json_text)
            self.assertIn(phrase, report_text)

    def test_missing_input_artifact_is_reported_visibly(self) -> None:
        self.run_review(["src/missing.py"])

        rows = read_csv(self.csv_output)
        self.assertEqual(rows[0]["status"], "REVIEW")
        self.assertIn("INPUT_ARTIFACT_MISSING", rows[0]["check_id"])

    def test_outputs_are_deterministic_and_json_schema_is_stable(self) -> None:
        self.write_artifact("src/scoring_engine.py", "purchase_state = 'BUYABLE'\nREVIEW\n")
        first = self.run_review(["src/scoring_engine.py"])
        first_csv = self.csv_output.read_text(encoding="utf-8")
        first_json = self.json_output.read_text(encoding="utf-8")
        second = self.run_review(["src/scoring_engine.py"])

        self.assertEqual(first.summary, second.summary)
        self.assertEqual(first_csv, self.csv_output.read_text(encoding="utf-8"))
        self.assertEqual(first_json, self.json_output.read_text(encoding="utf-8"))
        data = json.loads(self.json_output.read_text(encoding="utf-8"))
        self.assertEqual(data["as_of_date"], "2026-05-21")
        self.assertIn("non_scope_confirmation", data)
        self.assertEqual(list(read_csv(self.csv_output)[0]), semantic.CSV_FIELDS)

    def test_producer_uses_no_network_or_private_inputs(self) -> None:
        source = Path(semantic.__file__).read_text(encoding="utf-8")

        for forbidden in ["requests", "urllib", "http.client", "socket", "smtplib", "ftplib", "data/raw/private"]:
            self.assertNotIn(forbidden, source)

    def test_contract_contains_required_boundary_language(self) -> None:
        text = CONTRACT_PATH.read_text(encoding="utf-8").lower()
        normalized = " ".join(text.split())

        for phrase in [
            "read-only semantic review",
            "does not alter valuation/scoring outputs",
            "does not feed any values into `src/valuation_engine.py`",
            "does not alter `src/scoring_engine.py` formulas",
            "does not decide whether to buy, sell, hold, trim or rebalance",
            "adversarial input / failure mode semantics",
            "malformed or conflicting inputs must not be silently imputed",
            "investment advice",
            "human operator",
        ]:
            self.assertIn(phrase, normalized)

    def test_producer_does_not_modify_valuation_scoring_or_ranking_logic_files(self) -> None:
        protected = [
            ROOT / "src" / "valuation_engine.py",
            ROOT / "src" / "scoring_engine.py",
            ROOT / "src" / "monthly_ranking_engine.py",
        ]
        before = {path: digest(path) for path in protected}
        run_valuation_scoring_semantic_decision_quality_review(
            as_of_date="2026-05-21",
            output_csv=str(self.csv_output),
            output_json=str(self.json_output),
            report_output=str(self.report_output),
        )
        after = {path: digest(path) for path in protected}

        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
