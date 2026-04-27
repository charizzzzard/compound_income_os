from __future__ import annotations

import csv
import http.client
import json
import os
import threading
import time
import unittest
from pathlib import Path

from src.dashboard_engine import DASHBOARD_KPI_FIELDS, DASHBOARD_SECTION_FIELDS, DASHBOARD_SUMMARY_FIELDS
from src.dashboard_server import (
    ArtifactCache,
    DashboardPaths,
    build_action_counts,
    build_history_status,
    build_server,
    load_csv_table,
    load_holdings,
    load_json_payload,
    load_kpis,
    load_sections,
    load_summary,
    render_index_html,
    validate_host,
)


class DashboardServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_paths: list[Path] = []
        self._servers: list[tuple[object, threading.Thread]] = []

    def tearDown(self) -> None:
        for server, thread in reversed(self._servers):
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
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

    def _fixture_paths(self) -> dict[str, Path]:
        return {
            "kpis": self._path("_tmp_dashboard_server_kpis.csv"),
            "sections": self._path("_tmp_dashboard_server_sections.csv"),
            "summary": self._path("_tmp_dashboard_server_summary.csv"),
            "positions": self._path("_tmp_dashboard_server_positions.csv"),
            "holdings": self._path("_tmp_dashboard_server_holdings.csv"),
            "monthly_buy_ranking": self._path("_tmp_dashboard_server_monthly.csv"),
            "rebalance_proposals": self._path("_tmp_dashboard_server_rebalance.csv"),
            "watchlist": self._path("_tmp_dashboard_server_watchlist.csv"),
            "fundamentals_coverage": self._path("_tmp_dashboard_server_coverage.csv"),
            "research_priority": self._path("_tmp_dashboard_server_research.csv"),
            "cost_tax_ledger": self._path("_tmp_dashboard_server_ledger.csv"),
            "portfolio_timeseries": self._path("_tmp_dashboard_server_portfolio_timeseries.csv"),
            "benchmark_timeseries": self._path("_tmp_dashboard_server_benchmark_timeseries.csv"),
            "readiness_payload": self._path("_tmp_dashboard_server_readiness_payload.json"),
        }

    def _write_fixture_sources(self, *, weighted_buy_score: str = "70.84", history_points: int = 2) -> DashboardPaths:
        paths = self._fixture_paths()
        self._write_csv(
            paths["kpis"],
            DASHBOARD_KPI_FIELDS,
            [
                {
                    "metric_name": "weighted_buy_score",
                    "metric_group": "Score / Fundamentals",
                    "metric_value": weighted_buy_score,
                    "metric_unit": "",
                    "source_name": "unit_fixture",
                    "source_file": str(paths["kpis"]),
                    "measurement_mode": "SNAPSHOT_ONLY",
                    "data_quality_flag": "OK",
                    "availability_status": "AVAILABLE",
                    "notes": "",
                }
            ],
        )
        self._write_csv(
            paths["sections"],
            DASHBOARD_SECTION_FIELDS,
            [
                {
                    "section_name": "Portfolio / Struktur",
                    "block_status": "AVAILABLE",
                    "metric_name": "total_assets",
                    "display_order": "101",
                    "display_label": "Total Assets",
                    "value_display": "1000 EUR",
                    "data_quality_flag": "OK",
                },
                {
                    "section_name": "Score / Fundamentals",
                    "block_status": "AVAILABLE",
                    "metric_name": "weighted_buy_score",
                    "display_order": "201",
                    "display_label": "Weighted Buy Score",
                    "value_display": weighted_buy_score,
                    "data_quality_flag": "OK",
                },
                {
                    "section_name": "Benchmark / Performance",
                    "block_status": "PARTIAL",
                    "metric_name": "active_return",
                    "display_order": "301",
                    "display_label": "Active Return",
                    "value_display": "NOT_AVAILABLE",
                    "data_quality_flag": "OK",
                },
                {
                    "section_name": "Kosten / Steuern",
                    "block_status": "PARTIAL",
                    "metric_name": "total_fees",
                    "display_order": "401",
                    "display_label": "Total Fees",
                    "value_display": "2.5 EUR",
                    "data_quality_flag": "OK",
                },
                {
                    "section_name": "Datenqualitaet / Methodik",
                    "block_status": "NOT_AVAILABLE",
                    "metric_name": "missing_block_count",
                    "display_order": "501",
                    "display_label": "Missing Blocks",
                    "value_display": "1",
                    "data_quality_flag": "NOT_AVAILABLE",
                },
            ],
        )
        self._write_csv(
            paths["summary"],
            DASHBOARD_SUMMARY_FIELDS,
            [
                {
                    "snapshot_date": "2026-04-24",
                    "performance_source_date": "2026-04-24",
                    "cost_tax_source_date": "2026-04-24",
                    "cross_source_data_quality_flag": "OK",
                    "dashboard_data_quality_flag": "OK",
                    "portfolio_measurement_mode": "SNAPSHOT_ONLY",
                    "performance_measurement_mode": "SNAPSHOT_ONLY",
                    "ledger_measurement_mode": "FULL_LEDGER",
                    "total_assets": "1000",
                    "weighted_buy_score": weighted_buy_score,
                    "active_return": "NOT_AVAILABLE",
                    "total_fees": "2.5",
                    "total_taxes": "1.0",
                    "notes_count": "1",
                    "missing_block_count": "1",
                }
            ],
        )
        self._write_csv(
            paths["positions"],
            [
                "portfolio_date",
                "source_name",
                "source_type",
                "raw_name",
                "isin",
                "ticker",
                "company_name",
                "asset_type",
                "position_type",
                "sleeve",
                "sector",
                "country",
                "quantity",
                "current_price",
                "avg_cost",
                "market_value",
                "price_eur",
                "market_value_eur",
                "cost_basis_eur",
                "unrealized_pnl_eur",
                "mandate_fit",
                "data_quality_flag",
                "review_flag",
                "review_reason",
                "weight_portfolio_pct",
                "weight_total_assets_pct",
                "currency",
                "notes",
            ],
            [
                {
                    "portfolio_date": "2026-04-24",
                    "source_name": "unit_fixture",
                    "source_type": "csv",
                    "raw_name": "Cash",
                    "isin": "",
                    "ticker": "EUR-CASH",
                    "company_name": "Cash",
                    "asset_type": "CASH",
                    "position_type": "cash",
                    "sleeve": "CASH",
                    "sector": "",
                    "country": "EUR",
                    "quantity": "1",
                    "current_price": "500.0",
                    "avg_cost": "500.0",
                    "market_value": "500.0",
                    "price_eur": "500.0",
                    "market_value_eur": "500.0",
                    "cost_basis_eur": "500.0",
                    "unrealized_pnl_eur": "0.0",
                    "mandate_fit": "CASH_RESERVE",
                    "data_quality_flag": "OK",
                    "review_flag": "False",
                    "review_reason": "",
                    "weight_portfolio_pct": "50.0",
                    "weight_total_assets_pct": "50.0",
                    "currency": "EUR",
                    "notes": "",
                },
                {
                    "portfolio_date": "2026-04-24",
                    "source_name": "unit_fixture",
                    "source_type": "csv",
                    "raw_name": "Alpha Corp",
                    "isin": "US0000000001",
                    "ticker": "ALPHA",
                    "company_name": "Alpha Corp",
                    "asset_type": "STOCK",
                    "position_type": "security",
                    "sleeve": "SINGLE_STOCK",
                    "sector": "Industrials",
                    "country": "US",
                    "quantity": "2",
                    "current_price": "250.0",
                    "avg_cost": "250.0",
                    "market_value": "500.0",
                    "price_eur": "250.0",
                    "market_value_eur": "500.0",
                    "cost_basis_eur": "500.0",
                    "unrealized_pnl_eur": "0.0",
                    "mandate_fit": "MANDATE_CANDIDATE",
                    "data_quality_flag": "OK",
                    "review_flag": "False",
                    "review_reason": "",
                    "weight_portfolio_pct": "50.0",
                    "weight_total_assets_pct": "50.0",
                    "currency": "EUR",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            paths["holdings"],
            [
                "ticker",
                "company_name",
                "asset_type",
                "sleeve",
                "market_value",
                "current_weight",
                "business_score",
                "valuation_score",
                "buy_score",
                "mandate_fit",
                "purchase_readiness",
                "portfolio_action",
                "portfolio_action_reason",
                "data_quality_flag",
                "review_flag",
            ],
            [
                {
                    "ticker": "ALPHA",
                    "company_name": "Alpha Corp",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "market_value": "300.0",
                    "current_weight": "30.0",
                    "business_score": "80.0",
                    "valuation_score": "70.0",
                    "buy_score": "75.0",
                    "mandate_fit": "YES",
                    "purchase_readiness": "READY",
                    "portfolio_action": "ADD",
                    "portfolio_action_reason": "Quality and valuation align.",
                    "data_quality_flag": "OK",
                    "review_flag": "False",
                },
                {
                    "ticker": "BETA",
                    "company_name": "Beta Corp",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "market_value": "250.0",
                    "current_weight": "25.0",
                    "business_score": "65.0",
                    "valuation_score": "55.0",
                    "buy_score": "60.0",
                    "mandate_fit": "REVIEW",
                    "purchase_readiness": "BLOCKED",
                    "portfolio_action": "HOLD",
                    "portfolio_action_reason": "Keep position size stable.",
                    "data_quality_flag": "PARTIAL",
                    "review_flag": "False",
                },
                {
                    "ticker": "GAMMA",
                    "company_name": "Gamma Corp",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "market_value": "150.0",
                    "current_weight": "15.0",
                    "business_score": "40.0",
                    "valuation_score": "35.0",
                    "buy_score": "35.0",
                    "mandate_fit": "REVIEW",
                    "purchase_readiness": "BLOCKED",
                    "portfolio_action": "EXIT_REVIEW",
                    "portfolio_action_reason": "Coverage guardrail still active.",
                    "data_quality_flag": "MISSING_DATA",
                    "review_flag": "True",
                },
                {
                    "ticker": "HOLD_CASH",
                    "company_name": "Cash halten",
                    "asset_type": "CASH",
                    "sleeve": "CASH",
                    "market_value": "300.0",
                    "current_weight": "30.0",
                    "business_score": "0.0",
                    "valuation_score": "0.0",
                    "buy_score": "0.0",
                    "mandate_fit": "CASH_RESERVE",
                    "purchase_readiness": "BLOCKED",
                    "portfolio_action": "HOLD_CASH",
                    "portfolio_action_reason": "No attractive candidate.",
                    "data_quality_flag": "OK",
                    "review_flag": "False",
                },
            ],
        )
        self._write_csv(
            paths["monthly_buy_ranking"],
            [
                "rank",
                "ticker",
                "company_name",
                "current_weight",
                "target_action",
                "allocation_status",
                "suggested_buy_amount_eur",
                "rationale",
                "constraint_checks",
                "valuation_comment",
                "mandate_fit_comment",
            ],
            [
                {
                    "rank": "1",
                    "ticker": "HOLD_CASH",
                    "company_name": "Cash halten",
                    "current_weight": "30.0",
                    "target_action": "HOLD_CASH",
                    "allocation_status": "SELECTED_THIS_MONTH",
                    "suggested_buy_amount_eur": "500.0",
                    "rationale": "No candidate clears the guardrails.",
                    "constraint_checks": "portfolio_rule=hold_cash_allowed",
                    "valuation_comment": "Cash remains optionality.",
                    "mandate_fit_comment": "Allowed by config.",
                }
            ],
        )
        self._write_csv(
            paths["rebalance_proposals"],
            ["ticker", "company_name", "action", "current_weight_pct", "reason"],
            [{"ticker": "ALPHA", "company_name": "Alpha Corp", "action": "HOLD", "current_weight_pct": "30.0", "reason": "Within corridor."}],
        )
        self._write_csv(
            paths["watchlist"],
            [
                "ticker",
                "company_name",
                "sector",
                "country",
                "asset_type",
                "sleeve",
                "mandate_fit",
                "business_score",
                "valuation_score",
                "buy_score",
                "fair_value_estimate",
                "margin_of_safety_pct",
                "status",
                "valuation_comment",
                "mandate_fit_comment",
                "thesis_summary",
                "main_risks",
                "data_quality_flag",
            ],
            [
                {
                    "ticker": "DELTA",
                    "company_name": "Delta Corp",
                    "sector": "Industrials",
                    "country": "USA",
                    "asset_type": "STOCK",
                    "sleeve": "SINGLE_STOCK",
                    "mandate_fit": "YES",
                    "business_score": "82.0",
                    "valuation_score": "71.0",
                    "buy_score": "77.0",
                    "fair_value_estimate": "150.0",
                    "margin_of_safety_pct": "8.0",
                    "status": "WATCH",
                    "valuation_comment": "Looks acceptable.",
                    "mandate_fit_comment": "Fits the sleeve.",
                    "thesis_summary": "Wide moat compounder.",
                    "main_risks": "Cyclicality.",
                    "data_quality_flag": "OK",
                }
            ],
        )
        self._write_csv(
            paths["fundamentals_coverage"],
            [
                "holding_name",
                "ticker",
                "isin",
                "asset_type",
                "company_type_profile",
                "match_status",
                "match_method",
                "matched_company_name",
                "matched_ticker",
                "matched_isin",
                "match_conflict_flag",
                "data_quality_flag",
                "required_kpis_expected",
                "required_kpis_present",
                "missing_required_kpis",
                "not_applicable_kpis",
                "optional_missing_kpis",
                "profile_classification_warning_flag",
                "profile_classification_warning_reason",
                "needs_research_flag",
                "notes",
            ],
            [
                {
                    "holding_name": "Alpha Corp",
                    "ticker": "ALPHA",
                    "isin": "US0000000001",
                    "asset_type": "STOCK",
                    "company_type_profile": "OTHER",
                    "match_status": "PARTIAL",
                    "match_method": "ISIN",
                    "matched_company_name": "Alpha Corp",
                    "matched_ticker": "ALPHA",
                    "matched_isin": "US0000000001",
                    "match_conflict_flag": "False",
                    "data_quality_flag": "MISSING_DATA",
                    "required_kpis_expected": "0",
                    "required_kpis_present": "0",
                    "missing_required_kpis": "",
                    "not_applicable_kpis": "",
                    "optional_missing_kpis": "drawdown_from_high_pct",
                    "profile_classification_warning_flag": "True",
                    "profile_classification_warning_reason": "Profile not reviewed.",
                    "needs_research_flag": "True",
                    "notes": "Manual review needed.",
                }
            ],
        )
        self._write_csv(
            paths["research_priority"],
            [
                "ticker",
                "isin",
                "company_name",
                "asset_type",
                "company_type_profile",
                "profile_classification_warning_flag",
                "profile_classification_warning_reason",
                "market_value_eur",
                "weight_total_assets_pct",
                "weight_portfolio_pct",
                "missing_required_kpi_count",
                "missing_required_kpis",
                "needs_research_flag",
                "coverage_status",
                "research_priority",
                "research_priority_reason",
            ],
            [
                {
                    "ticker": "ALPHA",
                    "isin": "US0000000001",
                    "company_name": "Alpha Corp",
                    "asset_type": "STOCK",
                    "company_type_profile": "OTHER",
                    "profile_classification_warning_flag": "True",
                    "profile_classification_warning_reason": "Profile not reviewed.",
                    "market_value_eur": "500.0",
                    "weight_total_assets_pct": "50.0",
                    "weight_portfolio_pct": "50.0",
                    "missing_required_kpi_count": "1",
                    "missing_required_kpis": "roic",
                    "needs_research_flag": "True",
                    "coverage_status": "PARTIAL",
                    "research_priority": "HIGH",
                    "research_priority_reason": "Profile and KPI coverage incomplete.",
                }
            ],
        )
        self._write_csv(
            paths["cost_tax_ledger"],
            [
                "event_date",
                "broker",
                "document_type",
                "record_granularity",
                "event_type",
                "instrument_name",
                "ticker",
                "isin",
                "currency",
                "gross_amount",
                "net_amount",
                "fee_amount",
                "tax_amount",
                "withholding_tax_amount",
                "quantity",
                "price_per_unit",
                "reference_id",
                "source_name",
                "verification_status",
                "data_quality_flag",
                "notes",
                "event_group_id",
                "document_period_start",
                "document_period_end",
                "realized_proceeds_amount",
                "realized_cost_basis_amount",
                "realized_pnl_before_tax",
                "realized_pnl_after_tax_estimate_or_partial",
                "tax_jurisdiction",
            ],
            [
                {
                    "event_date": "2026-04-01",
                    "broker": "TRADE_REPUBLIC",
                    "document_type": "TRADE_CONFIRMATION",
                    "record_granularity": "EVENT",
                    "event_type": "SELL",
                    "instrument_name": "Alpha Corp",
                    "ticker": "ALPHA",
                    "isin": "US0000000001",
                    "currency": "EUR",
                    "gross_amount": "520.0",
                    "net_amount": "508.5",
                    "fee_amount": "1.5",
                    "tax_amount": "10.0",
                    "withholding_tax_amount": "0.0",
                    "quantity": "2.0",
                    "price_per_unit": "260.0",
                    "reference_id": "TRX-002",
                    "source_name": "unit_fixture",
                    "verification_status": "VERIFIED",
                    "data_quality_flag": "OK",
                    "notes": "Explicit realized fields support realized aggregation.",
                    "event_group_id": "TRX-002",
                    "document_period_start": "",
                    "document_period_end": "",
                    "realized_proceeds_amount": "520.0",
                    "realized_cost_basis_amount": "450.0",
                    "realized_pnl_before_tax": "70.0",
                    "realized_pnl_after_tax_estimate_or_partial": "60.0",
                    "tax_jurisdiction": "DE",
                }
            ],
        )
        portfolio_rows = []
        benchmark_rows = []
        for index in range(history_points):
            month = index + 1
            portfolio_rows.append(
                {
                    "date": f"2026-{month:02d}-28",
                    "portfolio_nav_eur": str(1000.0 + (index * 10.0)),
                    "portfolio_value_eur": str(1000.0 + (index * 10.0)),
                    "cash_value_eur": "0.0",
                    "net_external_cash_flow_eur": "",
                    "source_name": "unit_fixture",
                    "notes": "explicit unit test NAV point",
                }
            )
            benchmark_rows.append(
                {
                    "date": f"2026-{month:02d}-28",
                    "benchmark_name": "Unit Test Benchmark",
                    "benchmark_symbol": "UTB",
                    "currency": "EUR",
                    "close": str(100.0 + index),
                    "adjusted_close": str(100.0 + index),
                    "total_return_index": str(100.0 + index),
                    "benchmark_return_basis_used": "total_return_index",
                    "benchmark_reference_value": str(100.0 + index),
                    "data_quality_flag": "OK",
                    "notes": "Normalized from local benchmark CSV source unit_fixture.",
                }
            )
        self._write_csv(
            paths["portfolio_timeseries"],
            ["date", "portfolio_nav_eur", "portfolio_value_eur", "cash_value_eur", "net_external_cash_flow_eur", "source_name", "notes"],
            portfolio_rows,
        )
        self._write_csv(
            paths["benchmark_timeseries"],
            [
                "date",
                "benchmark_name",
                "benchmark_symbol",
                "currency",
                "close",
                "adjusted_close",
                "total_return_index",
                "benchmark_return_basis_used",
                "benchmark_reference_value",
                "data_quality_flag",
                "notes",
            ],
            benchmark_rows,
        )
        paths["readiness_payload"].write_text(
            json.dumps(
                {
                    "metadata": {"schema_version": "1", "private_data_included": False, "dummy_claims_included": False},
                    "readiness": {"decision": {"status": "BLOCKED", "reason_codes": ["UNIT_FIXTURE"]}},
                    "summary": {"active_blockers_count": 1},
                    "sections": {},
                    "guardrails": {"no_advice_language": True, "no_private_values": True},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return DashboardPaths(**{key: str(path) for key, path in paths.items()})

    def _start_server(self, paths: DashboardPaths) -> tuple[object, threading.Thread, int]:
        server = build_server("127.0.0.1", 0, paths)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self._servers.append((server, thread))
        return server, thread, int(server.server_address[1])

    def _request_json(self, port: int, path: str) -> tuple[int, dict[str, str], object]:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        headers = {key: value for key, value in response.getheaders()}
        conn.close()
        payload = json.loads(body)
        return response.status, headers, payload

    def test_extended_dashboard_paths_include_decision_artifacts(self) -> None:
        paths = DashboardPaths()
        self.assertEqual(len(paths.all_paths()), 14)
        self.assertIn(paths.positions, paths.all_paths())
        self.assertIn(paths.holdings, paths.all_paths())
        self.assertIn(paths.monthly_buy_ranking, paths.all_paths())
        self.assertIn(paths.rebalance_proposals, paths.all_paths())
        self.assertIn(paths.watchlist, paths.all_paths())
        self.assertIn(paths.fundamentals_coverage, paths.all_paths())
        self.assertIn(paths.research_priority, paths.all_paths())
        self.assertIn(paths.cost_tax_ledger, paths.all_paths())
        self.assertIn(paths.portfolio_timeseries, paths.all_paths())
        self.assertIn(paths.benchmark_timeseries, paths.all_paths())
        self.assertIn(paths.readiness_payload, paths.all_paths())

    def test_extended_csv_loaders_return_not_available_for_missing_optional_sources(self) -> None:
        missing = load_csv_table(self._path("_tmp_dashboard_server_missing_optional.csv"), ["ticker"], "optional dashboard table")
        self.assertEqual(missing["status"], "NOT_AVAILABLE")
        self.assertTrue(missing["path"].endswith("_tmp_dashboard_server_missing_optional.csv"))

    def test_readiness_payload_loader_returns_not_available_for_missing_json(self) -> None:
        missing = load_json_payload(self._path("_tmp_dashboard_server_missing_readiness.json"))
        self.assertEqual(missing["status"], "NOT_AVAILABLE")
        self.assertTrue(missing["path"].endswith("_tmp_dashboard_server_missing_readiness.json"))

    def test_history_status_blocks_chart_below_min_points(self) -> None:
        status = build_history_status(
            [{"date": "2026-01-31"}, {"date": "2026-02-28"}],
            [{"date": "2026-01-31"}, {"date": "2026-02-28"}],
        )
        self.assertEqual(status["chart_status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(status["portfolio_points"], 2)
        self.assertEqual(status["benchmark_points"], 2)
        self.assertIn("portfolio=2", status["message"])
        self.assertIn("benchmark=2", status["message"])
        self.assertIn("12", status["message"])

    def test_render_index_html_contains_decision_sections(self) -> None:
        paths = self._write_fixture_sources()
        html_text = render_index_html(
            load_kpis(paths.kpis),
            load_sections(paths.sections),
            load_summary(paths.summary),
            load_holdings(paths.holdings),
            load_csv_table(paths.positions, ["ticker"], "positions"),
            load_csv_table(paths.monthly_buy_ranking, ["ticker"], "monthly"),
            load_csv_table(paths.rebalance_proposals, ["ticker"], "rebalance"),
            load_csv_table(paths.watchlist, ["ticker"], "watchlist"),
            load_csv_table(paths.fundamentals_coverage, ["ticker"], "coverage"),
            load_csv_table(paths.research_priority, ["ticker"], "research"),
            load_csv_table(paths.cost_tax_ledger, ["event_date"], "ledger"),
            load_csv_table(paths.portfolio_timeseries, ["date"], "portfolio_timeseries"),
            load_csv_table(paths.benchmark_timeseries, ["date"], "benchmark_timeseries"),
            "2026-04-24T12:00:00+02:00",
        )
        for title in [
            "Decision Overview",
            "Holdings Detail",
            "Monthly Buy Ranking",
            "Watchlist",
            "Rebalance Proposals",
            "Fundamentals Coverage",
            "Research Priority",
            "Cost/Tax Ledger",
            "Performance History",
        ]:
            self.assertIn(title, html_text)

    def test_action_badges_and_counts_are_derived_from_rows(self) -> None:
        paths = self._write_fixture_sources()
        holdings = load_holdings(paths.holdings)
        counts = build_action_counts(holdings)
        self.assertEqual(counts["ADD"], 1)
        self.assertEqual(counts["HOLD"], 1)
        self.assertEqual(counts["EXIT_REVIEW"], 1)
        self.assertEqual(counts["HOLD_CASH"], 1)

        html_text = render_index_html(
            load_kpis(paths.kpis),
            load_sections(paths.sections),
            load_summary(paths.summary),
            holdings,
            load_csv_table(paths.positions, ["ticker"], "positions"),
            load_csv_table(paths.monthly_buy_ranking, ["ticker"], "monthly"),
            load_csv_table(paths.rebalance_proposals, ["ticker"], "rebalance"),
            load_csv_table(paths.watchlist, ["ticker"], "watchlist"),
            load_csv_table(paths.fundamentals_coverage, ["ticker"], "coverage"),
            load_csv_table(paths.research_priority, ["ticker"], "research"),
            load_csv_table(paths.cost_tax_ledger, ["event_date"], "ledger"),
            load_csv_table(paths.portfolio_timeseries, ["date"], "portfolio_timeseries"),
            load_csv_table(paths.benchmark_timeseries, ["date"], "benchmark_timeseries"),
            "2026-04-24T12:00:00+02:00",
        )
        for label in ["ADD", "HOLD", "EXIT_REVIEW", "HOLD_CASH"]:
            self.assertIn(label, html_text)

    def test_validate_host_rejects_non_local_binding(self) -> None:
        with self.assertRaisesRegex(ValueError, "127.0.0.1"):
            validate_host("0.0.0.0")
        with self.assertRaisesRegex(ValueError, "blank host"):
            validate_host("   ")

    def test_artifact_cache_reloads_after_mtime_change(self) -> None:
        paths = self._write_fixture_sources(weighted_buy_score="70.84")
        cache = ArtifactCache()

        before = cache.get(paths.kpis, load_kpis)
        self.assertEqual(before[0]["metric_value"], "70.84")

        kpis_path = Path(paths.kpis)
        self._write_csv(
            kpis_path,
            DASHBOARD_KPI_FIELDS,
            [
                {
                    "metric_name": "weighted_buy_score",
                    "metric_group": "Score / Fundamentals",
                    "metric_value": "88.88",
                    "metric_unit": "",
                    "source_name": "unit_fixture",
                    "source_file": str(kpis_path),
                    "measurement_mode": "SNAPSHOT_ONLY",
                    "data_quality_flag": "OK",
                    "availability_status": "AVAILABLE",
                    "notes": "",
                }
            ],
        )
        current = os.path.getmtime(kpis_path)
        os.utime(kpis_path, (current + 2.0, current + 2.0))

        after = cache.get(paths.kpis, load_kpis)
        self.assertEqual(after[0]["metric_value"], "88.88")

    def test_artifact_cache_invalidates_when_file_disappears(self) -> None:
        paths = self._write_fixture_sources()
        cache = ArtifactCache()

        _ = cache.get(paths.summary, load_summary)
        summary_path = Path(paths.summary)
        summary_path.unlink()

        payload = cache.get(paths.summary, load_summary)
        self.assertEqual(payload["status"], "NOT_AVAILABLE")

    def test_live_server_serves_extended_json_endpoints(self) -> None:
        paths = self._write_fixture_sources()
        _server, _thread, port = self._start_server(paths)
        time.sleep(0.1)

        for path in [
            "/api/positions.json",
            "/api/holdings.json",
            "/api/monthly-buy-ranking.json",
            "/api/rebalance-proposals.json",
            "/api/watchlist.json",
            "/api/fundamentals-coverage.json",
            "/api/research-priority.json",
            "/api/cost-tax-ledger.json",
            "/api/history-status.json",
            "/api/readiness.json",
            "/api/readiness",
            "/api/kpis.json",
            "/api/sections.json",
            "/api/summary.json",
            "/healthz",
        ]:
            status, headers, payload = self._request_json(port, path)
            self.assertEqual(status, 200, path)
            self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
            self.assertIn("X-Dashboard-Data-Mtime", headers)
            self.assertTrue(payload)

        _status, _headers, readiness = self._request_json(port, "/api/readiness.json")
        self.assertEqual(readiness["readiness"]["decision"]["status"], "BLOCKED")

    def test_live_server_serves_html_and_history_gate_without_chart(self) -> None:
        paths = self._write_fixture_sources(history_points=2)
        _server, _thread, port = self._start_server(paths)
        time.sleep(0.1)

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertIn("<!DOCTYPE html>", body)
        self.assertIn("Decision Overview", body)
        self.assertIn("INSUFFICIENT_HISTORY", body)
        self.assertNotIn("aria-label='Portfolio and benchmark history chart'", body)
        conn.close()

    def test_live_server_reloads_changed_file_without_restart(self) -> None:
        paths = self._write_fixture_sources(weighted_buy_score="70.84")
        _server, _thread, port = self._start_server(paths)
        time.sleep(0.1)

        status, _headers, payload = self._request_json(port, "/api/kpis.json")
        self.assertEqual(status, 200)
        self.assertEqual(payload[0]["metric_value"], "70.84")

        kpis_path = Path(paths.kpis)
        self._write_csv(
            kpis_path,
            DASHBOARD_KPI_FIELDS,
            [
                {
                    "metric_name": "weighted_buy_score",
                    "metric_group": "Score / Fundamentals",
                    "metric_value": "91.11",
                    "metric_unit": "",
                    "source_name": "unit_fixture",
                    "source_file": str(kpis_path),
                    "measurement_mode": "SNAPSHOT_ONLY",
                    "data_quality_flag": "OK",
                    "availability_status": "AVAILABLE",
                    "notes": "",
                }
            ],
        )
        current = os.path.getmtime(kpis_path)
        os.utime(kpis_path, (current + 2.0, current + 2.0))

        status, _headers, payload = self._request_json(port, "/api/kpis.json")
        self.assertEqual(status, 200)
        self.assertEqual(payload[0]["metric_value"], "91.11")

    def test_live_server_returns_not_available_after_file_delete(self) -> None:
        paths = self._write_fixture_sources()
        _server, _thread, port = self._start_server(paths)
        time.sleep(0.1)

        watchlist_path = Path(paths.watchlist)
        watchlist_path.unlink()

        status, _headers, payload = self._request_json(port, "/api/watchlist.json")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "NOT_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
