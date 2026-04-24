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
    build_server,
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

    def _dashboard_paths(self) -> tuple[Path, Path, Path]:
        return (
            self._path("_tmp_dashboard_server_kpis.csv"),
            self._path("_tmp_dashboard_server_sections.csv"),
            self._path("_tmp_dashboard_server_summary.csv"),
        )

    def _write_fixture_sources(self, *, weighted_buy_score: str = "70.84") -> DashboardPaths:
        kpis_path, sections_path, summary_path = self._dashboard_paths()
        self._write_csv(
            kpis_path,
            DASHBOARD_KPI_FIELDS,
            [
                {
                    "metric_name": "weighted_buy_score",
                    "metric_group": "Score / Fundamentals",
                    "metric_value": weighted_buy_score,
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
        self._write_csv(
            sections_path,
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
            summary_path,
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
        return DashboardPaths(kpis=str(kpis_path), sections=str(sections_path), summary=str(summary_path))

    def _start_server(self, paths: DashboardPaths) -> tuple[object, threading.Thread, int]:
        server = build_server("127.0.0.1", 0, paths)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self._servers.append((server, thread))
        return server, thread, int(server.server_address[1])

    def test_csv_loaders_serialize_existing_and_missing_sources(self) -> None:
        paths = self._write_fixture_sources()

        kpis = load_kpis(paths.kpis)
        sections = load_sections(paths.sections)
        summary = load_summary(paths.summary)
        missing = load_summary(self._path("_tmp_dashboard_server_missing.csv"))

        self.assertEqual(kpis[0]["metric_name"], "weighted_buy_score")
        self.assertEqual(sections[0]["section_name"], "Portfolio / Struktur")
        self.assertEqual(summary["snapshot_date"], "2026-04-24")
        self.assertEqual(missing["status"], "NOT_AVAILABLE")
        self.assertTrue(missing["path"].endswith("_tmp_dashboard_server_missing.csv"))

    def test_render_index_html_contains_all_sections_in_display_order_and_badges(self) -> None:
        paths = self._write_fixture_sources()
        html_text = render_index_html(load_kpis(paths.kpis), load_sections(paths.sections), load_summary(paths.summary), "2026-04-24T12:00:00+02:00")

        names = [
            "Portfolio / Struktur",
            "Score / Fundamentals",
            "Benchmark / Performance",
            "Kosten / Steuern",
            "Datenqualitaet / Methodik",
        ]
        indexes = [html_text.index(name) for name in names]
        self.assertEqual(indexes, sorted(indexes))
        for badge in ["AVAILABLE", "PARTIAL", "NOT_AVAILABLE"]:
            self.assertIn(badge, html_text)

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

    def test_live_server_serves_html_and_json_with_mtime_header(self) -> None:
        paths = self._write_fixture_sources()
        _server, _thread, port = self._start_server(paths)
        time.sleep(0.1)

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("X-Dashboard-Data-Mtime") == "NOT_AVAILABLE", False)
        self.assertIn("<!DOCTYPE html>", body)
        self.assertIn("Portfolio / Struktur", body)
        conn.close()

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/api/summary.json")
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Type"), "application/json; charset=utf-8")
        self.assertIn("snapshot_date", payload)
        conn.close()

    def test_live_server_reloads_changed_file_without_restart(self) -> None:
        paths = self._write_fixture_sources(weighted_buy_score="70.84")
        _server, _thread, port = self._start_server(paths)
        time.sleep(0.1)

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/api/kpis.json")
        payload = json.loads(conn.getresponse().read().decode("utf-8"))
        self.assertEqual(payload[0]["metric_value"], "70.84")
        conn.close()

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

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/api/kpis.json")
        payload = json.loads(conn.getresponse().read().decode("utf-8"))
        self.assertEqual(payload[0]["metric_value"], "91.11")
        conn.close()

    def test_live_server_returns_not_available_after_file_delete(self) -> None:
        paths = self._write_fixture_sources()
        _server, _thread, port = self._start_server(paths)
        time.sleep(0.1)

        summary_path = Path(paths.summary)
        summary_path.unlink()

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/api/summary.json")
        payload = json.loads(conn.getresponse().read().decode("utf-8"))
        self.assertEqual(payload["status"], "NOT_AVAILABLE")
        conn.close()


if __name__ == "__main__":
    unittest.main()
