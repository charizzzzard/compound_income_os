from __future__ import annotations

import csv
import json
import subprocess
import unittest
from pathlib import Path

from src.build_monthly_decision_report import build_monthly_decision_report
from src.build_portfolio_snapshot import build_portfolio_snapshot_report
from src.fundamentals_master import COVERAGE_OUTPUT_FIELDS
from src.personal_run_engine import STAGE_ORDER


class ReadmeAndReportTests(unittest.TestCase):
    def test_readme_uses_repo_portable_paths(self) -> None:
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertNotIn("C:\\Users\\", readme)
        self.assertNotIn("(/C:/Users/", readme)
        self.assertIn("reports/sample/portfolio_snapshot.md", readme)
        old_raw_path = "real_portfolio" + "_example.csv"
        self.assertNotIn(old_raw_path, readme)
        self.assertIn("--mode real", readme)
        self.assertIn("data/processed/personal_positions_snapshot.csv", readme)
        self.assertIn("Private Rohdaten sollten nicht committed werden.", readme)

    def test_readme_is_lf_normalized(self) -> None:
        readme_bytes = Path("README.md").read_bytes()
        self.assertNotIn(b"\r\n", readme_bytes)
        self.assertIn("*.md text eol=lf", Path(".gitattributes").read_text(encoding="utf-8"))

    def test_operator_surface_contract_docs_are_linked(self) -> None:
        required_paths = [
            Path("docs/contracts/DASHBOARD_OPERATOR_SURFACE_CONTRACT.md"),
            Path("docs/contracts/REVIEW_QUEUE_SUMMARY_CONTRACT.md"),
            Path("docs/contracts/DATA_FRESHNESS_STALENESS_CONTRACT.md"),
            Path("docs/governance/EXTERNAL_REPRODUCTION.md"),
            Path("docs/architecture/CIOS_FEATURE_STATUS.yaml"),
            Path("docs/architecture/CURRENT_KNOWN_GAPS.md"),
            Path("docs/architecture/PERSONAL_RUN_STAGE_DAG.md"),
        ]
        for path in required_paths:
            with self.subTest(path=str(path)):
                self.assertTrue(path.exists(), f"missing {path}")

        readme = Path("README.md").read_text(encoding="utf-8")
        module_contracts = Path("docs/MODULE_CONTRACTS.md").read_text(encoding="utf-8")
        context = Path("docs/CONTEXT_AND_ROADMAP.md").read_text(encoding="utf-8")
        for doc in [
            "docs/contracts/DASHBOARD_OPERATOR_SURFACE_CONTRACT.md",
            "docs/contracts/REVIEW_QUEUE_SUMMARY_CONTRACT.md",
            "docs/contracts/DATA_FRESHNESS_STALENESS_CONTRACT.md",
            "docs/governance/EXTERNAL_REPRODUCTION.md",
            "docs/architecture/PERSONAL_RUN_STAGE_DAG.md",
        ]:
            self.assertIn(doc, readme)
            self.assertIn(doc, module_contracts)
            self.assertIn(doc, context)

        feature_status = Path("docs/architecture/CIOS_FEATURE_STATUS.yaml").read_text(encoding="utf-8")
        self.assertIn("capability_id: governance_policy_docs", feature_status)
        self.assertNotIn("capability_id: policy_engine", feature_status)
        self.assertIn("repo_evidence_files:", feature_status)
        self.assertIn("packet_evidence_files:", feature_status)
        self.assertIn("generated_review_artifacts:", feature_status)

    def test_data_source_strategy_license_boundary_docs_are_linked_and_conservative(self) -> None:
        required_paths = [
            Path("docs/architecture/CIOS_DATA_SOURCE_STRATEGY.md"),
            Path("docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md"),
            Path("docs/architecture/CIOS_DATA_SOURCE_REGISTRY_TEMPLATE.yaml"),
            Path("docs/governance/DATA_SOURCE_REVIEW_CHECKLIST.md"),
            Path("src/data_source_registry_validation.py"),
            Path("tests/test_data_source_registry_validation.py"),
        ]
        for path in required_paths:
            with self.subTest(path=str(path)):
                self.assertTrue(path.exists(), f"missing {path}")

        readme = Path("README.md").read_text(encoding="utf-8")
        system_map = Path("docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md").read_text(encoding="utf-8")
        module_contracts = Path("docs/MODULE_CONTRACTS.md").read_text(encoding="utf-8")
        external_reproduction = Path("docs/governance/EXTERNAL_REPRODUCTION.md").read_text(encoding="utf-8")
        for path in required_paths:
            path_text = path.as_posix()
            with self.subTest(reference=path_text):
                self.assertIn(path_text, readme + "\n" + system_map + "\n" + module_contracts + "\n" + external_reproduction)

        strategy = Path("docs/architecture/CIOS_DATA_SOURCE_STRATEGY.md").read_text(encoding="utf-8")
        contract = Path("docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md").read_text(encoding="utf-8")
        checklist = Path("docs/governance/DATA_SOURCE_REVIEW_CHECKLIST.md").read_text(encoding="utf-8")
        combined = strategy + "\n" + contract + "\n" + checklist
        self.assertIn("Data Source Decision Matrix", strategy)
        self.assertIn("provider-agnostic", strategy)
        self.assertIn("UNKNOWN_REVIEW_REQUIRED", contract)
        self.assertIn("PRIVATE_LOCAL_ONLY", contract)
        self.assertIn("LEGAL_REVIEW_REQUIRED", contract)
        self.assertIn("Public availability is not redistribution permission.", contract)
        self.assertIn("license_evidence_files", contract)
        self.assertIn("freshness evidence is not license evidence", contract.lower())
        self.assertIn("Registry Validation Preflight", contract)
        self.assertIn("Use Class To Usage Scope Mapping", strategy)
        self.assertIn("not legal advice", combined.lower())
        self.assertNotIn("C:\\Users\\", combined)

        template = json.loads(Path("docs/architecture/CIOS_DATA_SOURCE_REGISTRY_TEMPLATE.yaml").read_text(encoding="utf-8"))
        self.assertTrue(template["template_only"])
        source_ids = {source["source_id"] for source in template["sources"]}
        self.assertIn("TEST_FIXTURE_SOURCE", source_ids)
        self.assertIn("PAID_VENDOR_SOURCE_TEMPLATE", source_ids)
        paid_template = next(source for source in template["sources"] if source["source_id"] == "PAID_VENDOR_SOURCE_TEMPLATE")
        self.assertIn("license_evidence_files", paid_template)
        self.assertIn("provenance_evidence_files", paid_template)
        self.assertIn("freshness_evidence_files", paid_template)
        self.assertIn("review_evidence_files", paid_template)
        self.assertFalse(paid_template["redistribution_allowed"])
        self.assertFalse(paid_template["commercial_use_allowed"])
        self.assertEqual(paid_template["review_status"], "LEGAL_REVIEW_REQUIRED")

    def test_meta_governance_baseline_docs_are_linked_and_conservative(self) -> None:
        required_paths = [
            Path("docs/governance/CIOS_SYSTEM_CONSTITUTION.md"),
            Path("docs/governance/CIOS_OPERATING_MODEL.md"),
            Path("docs/governance/CIOS_RISK_AND_CONTROL_FRAMEWORK.md"),
            Path("docs/governance/CIOS_TRACEABILITY_STANDARD.md"),
            Path("docs/governance/CIOS_EVOLUTION_GUARDRAILS.md"),
            Path("docs/architecture/CIOS_META_ARCHITECTURE.md"),
            Path("docs/architecture/CIOS_MATURITY_MODEL.yaml"),
            Path("docs/governance/CIOS_FINAL_META_BASELINE_ACCEPTANCE.md"),
        ]
        for path in required_paths:
            with self.subTest(path=str(path)):
                self.assertTrue(path.exists(), f"missing {path}")

        readme = Path("README.md").read_text(encoding="utf-8")
        system_map = Path("docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md").read_text(encoding="utf-8")
        module_contracts = Path("docs/MODULE_CONTRACTS.md").read_text(encoding="utf-8")
        for path in required_paths:
            path_text = path.as_posix()
            with self.subTest(reference=path_text):
                self.assertIn(path_text, readme)
                self.assertIn(path_text, system_map + "\n" + module_contracts)

        constitution = Path("docs/governance/CIOS_SYSTEM_CONSTITUTION.md").read_text(encoding="utf-8")
        acceptance = Path("docs/governance/CIOS_FINAL_META_BASELINE_ACCEPTANCE.md").read_text(encoding="utf-8")
        self.assertIn("Compound Income OS", constitution)
        self.assertIn("CIOS", constitution)
        self.assertIn("CIOS_META_BASELINE_ACCEPTED_WITH_FINDINGS", acceptance)
        self.assertIn("FEATURE_COMPLETE: false", acceptance)
        self.assertIn("PRODUCT_COMPLETE: false", acceptance)
        self.assertIn("COMMERCIAL_READY: false", acceptance)
        self.assertNotIn("C:\\Users\\", constitution + acceptance)

        maturity = json.loads(Path("docs/architecture/CIOS_MATURITY_MODEL.yaml").read_text(encoding="utf-8"))
        self.assertIn("kernels", maturity)
        self.assertGreaterEqual(len(maturity["kernels"]), 20)
        for kernel in maturity["kernels"]:
            with self.subTest(kernel=kernel["kernel_id"]):
                self.assertLessEqual(kernel["maturity_level"], 5)
        self.assertTrue(any(kernel["kernel_id"] == "portfolio_event_ledger" and kernel["status"] == "KNOWN_GAP" for kernel in maturity["kernels"]))
        self.assertTrue(any(kernel["kernel_id"] == "meta_governance" for kernel in maturity["kernels"]))

    def test_personal_run_stage_dag_documents_current_stage_order(self) -> None:
        dag_path = Path("docs/architecture/PERSONAL_RUN_STAGE_DAG.md")
        self.assertTrue(dag_path.exists())
        dag = dag_path.read_text(encoding="utf-8")
        readme = Path("README.md").read_text(encoding="utf-8")
        system_map = Path("docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md").read_text(encoding="utf-8")
        external_reproduction = Path("docs/governance/EXTERNAL_REPRODUCTION.md").read_text(encoding="utf-8")

        for doc in [readme, system_map, external_reproduction]:
            self.assertIn("docs/architecture/PERSONAL_RUN_STAGE_DAG.md", doc)
        for stage in STAGE_ORDER:
            with self.subTest(stage=stage):
                self.assertIn(stage, dag)
        for forbidden in ["C:\\Users\\", "C:/Users/", "/Users/", "/home/"]:
            self.assertNotIn(forbidden, dag)

    def test_sec_related_csv_templates_are_lf_normalized_without_trailing_whitespace(self) -> None:
        gitattributes = Path(".gitattributes").read_text(encoding="utf-8")
        template_paths = [
            Path("data/raw/personal_fundamentals_evidence_template.csv"),
            Path("data/raw/personal_fundamentals_snapshot_review_template.csv"),
            Path("data/raw/personal_sec_identity_map_template.csv"),
        ]
        for path in template_paths:
            content = path.read_bytes()
            with self.subTest(path=str(path)):
                self.assertNotIn(b"\r\n", content)
                self.assertIn(b"\n", content)
                for line in content.splitlines():
                    self.assertEqual(line.rstrip(b" \t"), line)
                self.assertIn(f"{path.as_posix()} text eol=lf", gitattributes)

    def test_report_builders_generate_german_markdown(self) -> None:
        portfolio_output = Path("tests") / "_tmp_portfolio_snapshot.md"
        decision_output = Path("tests") / "_tmp_decision_report.md"
        try:
            build_portfolio_snapshot_report(
                positions_rows=[
                    {
                        "ticker": "EUR-CASH",
                        "company_name": "Cash",
                        "sleeve": "CASH",
                        "market_value_eur": "1000",
                        "weight_total_assets_pct": "100.0",
                        "asset_type": "CASH",
                        "sector": "Cash",
                    }
                ],
                output_path=str(portfolio_output),
                scores_rows=[],
            )
            build_monthly_decision_report(
                positions_rows=[],
                score_rows=[],
                ranking_rows=[],
                output_path=str(decision_output),
            )
            portfolio_report = portfolio_output.read_text(encoding="utf-8")
            decision_report = decision_output.read_text(encoding="utf-8")
            self.assertIn("# Portfolio-Ueberblick", portfolio_report)
            self.assertIn("## Regelpruefung", portfolio_report)
            self.assertNotIn("## Fundamentals-Abdeckung", portfolio_report)
            self.assertIn("# Monatlicher Entscheidungsbericht", decision_report)
            self.assertIn("## Offene REVIEW-Faelle", decision_report)
            self.assertNotIn("## Offene Fundamentals-Research-Luecken", decision_report)
        finally:
            if portfolio_output.exists():
                portfolio_output.unlink()
            if decision_output.exists():
                decision_output.unlink()

    def test_report_builders_include_fundamentals_coverage_when_provided(self) -> None:
        portfolio_output = Path("tests") / "_tmp_portfolio_snapshot_coverage.md"
        decision_output = Path("tests") / "_tmp_decision_report_coverage.md"
        coverage_rows = [
            {
                "holding_name": "Covered Co",
                "ticker": "COV",
                "match_status": "COVERED",
                "match_method": "ISIN",
                "missing_required_kpis": "",
                "needs_research_flag": "False",
            },
            {
                "holding_name": "Partial Co",
                "ticker": "PAR",
                "match_status": "PARTIAL",
                "match_method": "TICKER",
                "missing_required_kpis": "roic; fcf_margin",
                "needs_research_flag": "True",
            },
            {
                "holding_name": "Review Co",
                "ticker": "REV",
                "match_status": "REVIEW",
                "match_method": "NO_MATCH",
                "missing_required_kpis": "",
                "needs_research_flag": "True",
            },
            {
                "holding_name": "No Match Co",
                "ticker": "MISS",
                "match_status": "NO_MATCH",
                "match_method": "NO_MATCH",
                "missing_required_kpis": "",
                "needs_research_flag": "True",
            },
        ]
        try:
            build_portfolio_snapshot_report(
                positions_rows=[
                    {
                        "ticker": "EUR-CASH",
                        "company_name": "Cash",
                        "sleeve": "CASH",
                        "market_value_eur": "1000",
                        "weight_total_assets_pct": "100.0",
                        "asset_type": "CASH",
                        "sector": "Cash",
                    }
                ],
                output_path=str(portfolio_output),
                scores_rows=[],
                coverage_rows=coverage_rows,
            )
            build_monthly_decision_report(
                positions_rows=[],
                score_rows=[],
                ranking_rows=[],
                output_path=str(decision_output),
                coverage_rows=coverage_rows,
            )
            portfolio_report = portfolio_output.read_text(encoding="utf-8")
            decision_report = decision_output.read_text(encoding="utf-8")

            self.assertIn("## Fundamentals-Abdeckung", portfolio_report)
            self.assertIn("- COVERED: 1", portfolio_report)
            self.assertIn("- PARTIAL: 1", portfolio_report)
            self.assertIn("- REVIEW: 1", portfolio_report)
            self.assertIn("- NO_MATCH: 1", portfolio_report)
            self.assertIn("- Holdings mit Pflicht-KPI-Luecken: 1", portfolio_report)
            self.assertIn("`PAR` Partial Co: status=PARTIAL method=TICKER missing_required=roic; fcf_margin", portfolio_report)
            self.assertIn("`MISS` No Match Co: status=NO_MATCH method=NO_MATCH", portfolio_report)

            self.assertIn("## Offene Fundamentals-Research-Luecken", decision_report)
            self.assertIn("`PAR` Partial Co: status=PARTIAL method=TICKER missing_required=roic; fcf_margin", decision_report)
            self.assertIn("`REV` Review Co: status=REVIEW method=NO_MATCH", decision_report)
            self.assertLess(decision_report.index("`PAR`"), decision_report.index("`REV`"))
        finally:
            if portfolio_output.exists():
                portfolio_output.unlink()
            if decision_output.exists():
                decision_output.unlink()

    def test_report_clis_accept_header_only_coverage_csv(self) -> None:
        positions_path = Path("tests") / "_tmp_report_positions_empty_coverage.csv"
        scores_path = Path("tests") / "_tmp_report_scores_empty_coverage.csv"
        ranking_path = Path("tests") / "_tmp_report_ranking_empty_coverage.csv"
        coverage_path = Path("tests") / "_tmp_report_empty_coverage.csv"
        portfolio_output = Path("tests") / "_tmp_portfolio_empty_coverage.md"
        decision_output = Path("tests") / "_tmp_decision_empty_coverage.md"
        try:
            with positions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["ticker", "company_name", "sleeve", "market_value_eur", "weight_total_assets_pct", "asset_type", "sector"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "ticker": "EUR-CASH",
                        "company_name": "Cash",
                        "sleeve": "CASH",
                        "market_value_eur": "100",
                        "weight_total_assets_pct": "100.0",
                        "asset_type": "CASH",
                        "sector": "Cash",
                    }
                )
            with scores_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ticker", "classification", "data_quality_flag", "held_in_portfolio", "main_risks"])
                writer.writeheader()
                writer.writerow({"ticker": "EUR-CASH", "classification": "HOLD", "data_quality_flag": "OK", "held_in_portfolio": "true", "main_risks": ""})
            with ranking_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "rank",
                        "ticker",
                        "target_action",
                        "suggested_buy_amount_eur",
                        "rationale",
                        "constraint_checks",
                        "valuation_comment",
                        "mandate_fit_comment",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "rank": "1",
                        "ticker": "EUR-CASH",
                        "target_action": "HOLD_CASH",
                        "suggested_buy_amount_eur": "0",
                        "rationale": "cash only",
                        "constraint_checks": "no_candidate",
                        "valuation_comment": "cash",
                        "mandate_fit_comment": "cash",
                    }
                )
            with coverage_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=COVERAGE_OUTPUT_FIELDS)
                writer.writeheader()

            portfolio_result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.build_portfolio_snapshot",
                    "--positions",
                    str(positions_path),
                    "--coverage",
                    str(coverage_path),
                    "--output",
                    str(portfolio_output),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )
            decision_result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.build_monthly_decision_report",
                    "--positions",
                    str(positions_path),
                    "--scores",
                    str(scores_path),
                    "--ranking",
                    str(ranking_path),
                    "--coverage",
                    str(coverage_path),
                    "--output",
                    str(decision_output),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertEqual(portfolio_result.returncode, 0, portfolio_result.stderr)
            self.assertEqual(decision_result.returncode, 0, decision_result.stderr)
            portfolio_report = portfolio_output.read_text(encoding="utf-8")
            decision_report = decision_output.read_text(encoding="utf-8")
            self.assertIn("## Fundamentals-Abdeckung", portfolio_report)
            self.assertIn("- COVERED: 0", portfolio_report)
            self.assertIn("- PARTIAL: 0", portfolio_report)
            self.assertIn("- REVIEW: 0", portfolio_report)
            self.assertIn("- NO_MATCH: 0", portfolio_report)
            self.assertIn("- Holdings mit Fundamentals-Research-Bedarf: 0", portfolio_report)
            self.assertIn("- Holdings mit Pflicht-KPI-Luecken: 0", portfolio_report)
            self.assertIn("## Fundamentals-Research-Luecken", portfolio_report)
            self.assertIn("- Keine offenen Fundamentals-Research-Luecken.", portfolio_report)
            self.assertIn("## Offene Fundamentals-Research-Luecken", decision_report)
            self.assertIn("- Keine offenen Fundamentals-Research-Luecken aus Coverage.", decision_report)
        finally:
            for path in [positions_path, scores_path, ranking_path, coverage_path, portfolio_output, decision_output]:
                if path.exists():
                    path.unlink()

    def test_report_clis_reject_incomplete_coverage_csv(self) -> None:
        positions_path = Path("tests") / "_tmp_report_positions_coverage.csv"
        scores_path = Path("tests") / "_tmp_report_scores_coverage.csv"
        ranking_path = Path("tests") / "_tmp_report_ranking_coverage.csv"
        coverage_path = Path("tests") / "_tmp_report_bad_coverage.csv"
        portfolio_output = Path("tests") / "_tmp_portfolio_bad_coverage.md"
        decision_output = Path("tests") / "_tmp_decision_bad_coverage.md"
        try:
            with positions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["ticker", "company_name", "sleeve", "market_value_eur", "weight_total_assets_pct", "asset_type", "sector"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "ticker": "AAPL",
                        "company_name": "Apple",
                        "sleeve": "SINGLE_STOCK",
                        "market_value_eur": "100",
                        "weight_total_assets_pct": "10.0",
                        "asset_type": "STOCK",
                        "sector": "Technology",
                    }
                )
            with scores_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ticker", "classification", "data_quality_flag", "held_in_portfolio", "main_risks"])
                writer.writeheader()
                writer.writerow({"ticker": "AAPL", "classification": "HOLD", "data_quality_flag": "OK", "held_in_portfolio": "true", "main_risks": ""})
            with ranking_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["rank", "ticker", "target_action", "suggested_buy_amount_eur", "rationale", "constraint_checks"])
                writer.writeheader()
                writer.writerow({"rank": "1", "ticker": "AAPL", "target_action": "BUY", "suggested_buy_amount_eur": "100", "rationale": "ok", "constraint_checks": "ok"})
            with coverage_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["holding_name", "ticker", "match_status", "match_method", "missing_required_kpis"])
                writer.writeheader()
                writer.writerow({"holding_name": "Apple", "ticker": "AAPL", "match_status": "COVERED", "match_method": "ISIN", "missing_required_kpis": ""})

            portfolio_result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.build_portfolio_snapshot",
                    "--positions",
                    str(positions_path),
                    "--coverage",
                    str(coverage_path),
                    "--output",
                    str(portfolio_output),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )
            decision_result = subprocess.run(
                [
                    "python",
                    "-m",
                    "src.build_monthly_decision_report",
                    "--positions",
                    str(positions_path),
                    "--scores",
                    str(scores_path),
                    "--ranking",
                    str(ranking_path),
                    "--coverage",
                    str(coverage_path),
                    "--output",
                    str(decision_output),
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(portfolio_result.returncode, 0)
            self.assertIn("coverage CSV", f"{portfolio_result.stdout}\n{portfolio_result.stderr}")
            self.assertIn("needs_research_flag", f"{portfolio_result.stdout}\n{portfolio_result.stderr}")
            self.assertFalse(portfolio_output.exists())
            self.assertNotEqual(decision_result.returncode, 0)
            self.assertIn("coverage CSV", f"{decision_result.stdout}\n{decision_result.stderr}")
            self.assertIn("needs_research_flag", f"{decision_result.stdout}\n{decision_result.stderr}")
            self.assertFalse(decision_output.exists())
        finally:
            for path in [positions_path, scores_path, ranking_path, coverage_path, portfolio_output, decision_output]:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
