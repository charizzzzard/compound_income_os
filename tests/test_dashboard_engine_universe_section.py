from __future__ import annotations

import csv
import unittest
from datetime import date
from pathlib import Path

from src.dashboard_engine import (
    DASHBOARD_UNIVERSE_FIELDS,
    build_universe_section,
    run_dashboard_engine,
    write_universe_csv,
)


class DashboardEngineUniverseSectionTests(unittest.TestCase):
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

    def _position(self, ticker: str, sleeve: str = "SINGLE_STOCK") -> dict[str, str]:
        return {
            "ticker": ticker,
            "company_name": f"{ticker} Holding",
            "sector": "Technology",
            "sleeve": sleeve,
        }

    def _watchlist(self, ticker: str, status: str = "REVIEW", sleeve: str = "SINGLE_STOCK") -> dict[str, str]:
        return {
            "ticker": ticker,
            "company_name": f"{ticker} Watch",
            "sector": "Healthcare",
            "sleeve": sleeve,
            "status": status,
        }

    def _score(self, ticker: str, buy_score: str = "75", source_as_of_date: str = "2026-05-01") -> dict[str, str]:
        return {
            "ticker": ticker,
            "company_name": f"{ticker} Score",
            "business_score": "80",
            "valuation_score": "70",
            "buy_score": buy_score,
            "source_as_of_date": source_as_of_date,
        }

    def _plan(self, ticker: str, active: str) -> dict[str, str]:
        return {
            "ticker": ticker,
            "isin": "US5949181045",
            "broker": "TRADE_REPUBLIC",
            "instrument_name": ticker,
            "monthly_amount_eur": "25",
            "frequency": "MONTHLY",
            "execution_day_of_month": "2",
            "active": active,
            "started_at": "2026-01-01",
            "last_modified": "2026-05-01",
            "notes": "",
        }

    def test_holdings_only_bucket_holding(self) -> None:
        rows = build_universe_section(positions_rows=[self._position("MSFT")])

        self.assertEqual(rows[0]["bucket"], "HOLDING")

    def test_watchlist_only_bucket_watchlist(self) -> None:
        rows = build_universe_section(watchlist_rows=[self._watchlist("MSFT")])

        self.assertEqual(rows[0]["bucket"], "WATCHLIST")

    def test_mixed_overlap_bucket_holding_and_watchlist(self) -> None:
        rows = build_universe_section(
            positions_rows=[self._position("MSFT")],
            watchlist_rows=[self._watchlist("msft")],
        )

        self.assertEqual(rows[0]["bucket"], "HOLDING_AND_WATCHLIST")

    def test_empty_scores_are_missing_data_and_never_scored(self) -> None:
        rows = build_universe_section(positions_rows=[self._position("MSFT")])

        self.assertEqual(rows[0]["business_score"], "MISSING_DATA")
        self.assertEqual(rows[0]["valuation_score"], "MISSING_DATA")
        self.assertEqual(rows[0]["buy_score"], "MISSING_DATA")
        self.assertEqual(rows[0]["stale_marker"], "NEVER_SCORED")

    def test_active_savings_plan_flag_true(self) -> None:
        rows = build_universe_section(
            positions_rows=[self._position("MSFT")],
            savings_plan_rows=[self._plan("MSFT", "TRUE")],
        )

        self.assertEqual(rows[0]["savings_plan_active"], "TRUE")

    def test_inactive_savings_plan_flag_false(self) -> None:
        rows = build_universe_section(
            positions_rows=[self._position("MSFT")],
            savings_plan_rows=[self._plan("MSFT", "FALSE")],
        )

        self.assertEqual(rows[0]["savings_plan_active"], "FALSE")

    def test_no_plan_flag_no_plan(self) -> None:
        rows = build_universe_section(positions_rows=[self._position("MSFT")])

        self.assertEqual(rows[0]["savings_plan_active"], "NO_PLAN")

    def test_stale_marker_over_30_days_when_source_date_exists(self) -> None:
        rows = build_universe_section(
            positions_rows=[self._position("MSFT")],
            scores_rows=[self._score("MSFT", source_as_of_date="2026-04-01")],
            today=date(2026, 5, 13),
        )

        self.assertEqual(rows[0]["last_score_update_date"], "2026-04-01")
        self.assertEqual(rows[0]["stale_marker"], "STALE_30D")

    def test_deterministic_sorting_uses_ticker_tie_breaker(self) -> None:
        rows = build_universe_section(
            positions_rows=[self._position("MSFT"), self._position("AAPL")],
            scores_rows=[self._score("MSFT", buy_score="75"), self._score("AAPL", buy_score="75")],
            today=date(2026, 5, 13),
        )

        self.assertEqual([row["ticker"] for row in rows], ["AAPL", "MSFT"])

    def test_header_order_stable_in_written_csv(self) -> None:
        path = self._path("_tmp_dashboard_universe_order.csv")

        write_universe_csv(path, [])

        self.assertEqual(path.read_text(encoding="utf-8").splitlines()[0].split(","), DASHBOARD_UNIVERSE_FIELDS)

    def test_empty_input_writes_header_only_csv(self) -> None:
        universe_output = self._path("_tmp_dashboard_universe_empty.csv")
        result = run_dashboard_engine(
            positions_path=str(self._path("_tmp_missing_positions.csv")),
            scores_path=str(self._path("_tmp_missing_scores.csv")),
            holdings_path=str(self._path("_tmp_missing_holdings.csv")),
            watchlist_path=str(self._path("_tmp_missing_watchlist.csv")),
            savings_plan_input=str(self._path("_tmp_missing_savings_plan.csv")),
            kpi_output=str(self._path("_tmp_dashboard_kpis.csv")),
            sections_output=str(self._path("_tmp_dashboard_sections.csv")),
            summary_output=str(self._path("_tmp_dashboard_summary.csv")),
            report_output=str(self._path("_tmp_dashboard_report.md")),
            universe_output=str(universe_output),
        )

        self.assertEqual(result["universe_rows"], [])
        self.assertEqual(universe_output.read_text(encoding="utf-8").splitlines(), [",".join(DASHBOARD_UNIVERSE_FIELDS)])

    def test_invalid_or_missing_sleeve_maps_to_unknown_sleeve(self) -> None:
        rows = build_universe_section(positions_rows=[self._position("MSFT", sleeve="OTHER")])

        self.assertEqual(rows[0]["sleeve"], "UNKNOWN_SLEEVE")


if __name__ == "__main__":
    unittest.main()
