from __future__ import annotations

import argparse
import html
import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from src.common import read_csv_rows, resolve_repo_path
from src.dashboard_engine import (
    DASHBOARD_KPI_FIELDS,
    DASHBOARD_SECTION_FIELDS,
    DASHBOARD_SUMMARY_FIELDS,
    DEFAULT_KPI_OUTPUT,
    DEFAULT_SECTIONS_OUTPUT,
    DEFAULT_SUMMARY_OUTPUT,
    NOT_AVAILABLE,
)

LOGGER = logging.getLogger(__name__)
JSON_CONTENT_TYPE = "application/json; charset=utf-8"
HTML_CONTENT_TYPE = "text/html; charset=utf-8"


@dataclass(frozen=True)
class DashboardPaths:
    kpis: str
    sections: str
    summary: str

    def all_paths(self) -> list[str]:
        return [self.kpis, self.sections, self.summary]


@dataclass
class CacheEntry:
    mtime: float | None
    payload: Any


def validate_host(host: str) -> str:
    normalized = str(host or "").strip()
    if not normalized:
        raise ValueError("dashboard_server requires --host 127.0.0.1; blank host is not allowed.")
    if normalized != "127.0.0.1":
        raise ValueError(f"dashboard_server only supports --host 127.0.0.1 for local-only usage; got {normalized!r}.")
    return normalized


def not_available_payload(path_value: str | Path) -> dict[str, str]:
    return {"status": NOT_AVAILABLE, "path": str(resolve_repo_path(path_value))}


def artifact_mtime(path_value: str | Path) -> float | None:
    resolved = resolve_repo_path(path_value)
    try:
        return os.path.getmtime(resolved)
    except FileNotFoundError:
        return None


def latest_mtime(paths: list[str | Path]) -> str:
    mtimes = [mtime for mtime in (artifact_mtime(path) for path in paths) if mtime is not None]
    if not mtimes:
        return NOT_AVAILABLE
    return datetime.fromtimestamp(max(mtimes)).astimezone().isoformat()


def load_kpis(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    resolved = resolve_repo_path(path_value)
    if not resolved.exists():
        return not_available_payload(path_value)
    rows = read_csv_rows(path_value)
    if rows and any(field not in rows[0] for field in DASHBOARD_KPI_FIELDS):
        missing = [field for field in DASHBOARD_KPI_FIELDS if field not in rows[0]]
        raise ValueError(f"dashboard KPI CSV ({resolved}) missing required columns: {', '.join(missing)}")
    return rows


def load_sections(path_value: str | Path) -> list[dict[str, str]] | dict[str, str]:
    resolved = resolve_repo_path(path_value)
    if not resolved.exists():
        return not_available_payload(path_value)
    rows = read_csv_rows(path_value)
    if rows and any(field not in rows[0] for field in DASHBOARD_SECTION_FIELDS):
        missing = [field for field in DASHBOARD_SECTION_FIELDS if field not in rows[0]]
        raise ValueError(f"dashboard sections CSV ({resolved}) missing required columns: {', '.join(missing)}")
    return rows


def load_summary(path_value: str | Path) -> dict[str, str]:
    resolved = resolve_repo_path(path_value)
    if not resolved.exists():
        return not_available_payload(path_value)
    rows = read_csv_rows(path_value)
    if not rows:
        return not_available_payload(path_value)
    if any(field not in rows[0] for field in DASHBOARD_SUMMARY_FIELDS):
        missing = [field for field in DASHBOARD_SUMMARY_FIELDS if field not in rows[0]]
        raise ValueError(f"dashboard summary CSV ({resolved}) missing required columns: {', '.join(missing)}")
    return rows[0]


class ArtifactCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, CacheEntry] = {}

    def get(self, path_value: str | Path, loader: Callable[[str | Path], Any]) -> Any:
        resolved = str(resolve_repo_path(path_value))
        observed_mtime = artifact_mtime(path_value)
        with self._lock:
            entry = self._entries.get(resolved)
            if entry is not None and entry.mtime == observed_mtime:
                return entry.payload
            payload = loader(path_value)
            self._entries[resolved] = CacheEntry(mtime=observed_mtime, payload=payload)
            return payload


def is_not_available(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("status") == NOT_AVAILABLE


def section_sort_key(row: dict[str, str]) -> tuple[int, str, str]:
    raw_order = str(row.get("display_order", "") or "").strip()
    try:
        order = int(raw_order)
    except ValueError:
        order = 10**9
    return (
        order,
        str(row.get("section_name", "") or "").strip(),
        str(row.get("display_label", "") or "").strip(),
    )


def render_summary_block(summary: dict[str, str]) -> str:
    if is_not_available(summary):
        return (
            "<section class='summary unavailable'>"
            "<h2>Summary</h2>"
            f"<p>{html.escape(summary['status'])}: {html.escape(summary['path'])}</p>"
            "</section>"
        )
    cards = [
        ("Snapshot Date", summary.get("snapshot_date", "")),
        ("Dashboard Quality", summary.get("dashboard_data_quality_flag", "")),
        ("Performance Mode", summary.get("performance_measurement_mode", "")),
        ("Ledger Mode", summary.get("ledger_measurement_mode", "")),
        ("Total Assets", summary.get("total_assets", "")),
        ("Weighted Buy Score", summary.get("weighted_buy_score", "")),
        ("Missing Blocks", summary.get("missing_block_count", "")),
    ]
    body = "".join(
        "<div class='summary-card'>"
        f"<div class='summary-label'>{html.escape(label)}</div>"
        f"<div class='summary-value'>{html.escape(value or NOT_AVAILABLE)}</div>"
        "</div>"
        for label, value in cards
    )
    return f"<section class='summary'><h2>Summary</h2><div class='summary-grid'>{body}</div></section>"


def render_index_html(
    kpis: list[dict[str, str]] | dict[str, str],
    sections: list[dict[str, str]] | dict[str, str],
    summary: dict[str, str],
    data_mtime: str,
) -> str:
    if is_not_available(sections):
        section_html = (
            "<section class='section unavailable'>"
            "<h2><span>Dashboard Sections</span><span class='badge not-available'>NOT_AVAILABLE</span></h2>"
            f"<p>{html.escape(sections['path'])}</p>"
            "</section>"
        )
    else:
        grouped: dict[str, list[dict[str, str]]] = {}
        ordered_rows = sorted(sections, key=section_sort_key)
        for row in ordered_rows:
            grouped.setdefault(str(row.get("section_name", "") or "").strip(), []).append(row)

        blocks: list[str] = []
        for section_name, rows in grouped.items():
            block_status = str(rows[0].get("block_status", NOT_AVAILABLE) or NOT_AVAILABLE).strip() or NOT_AVAILABLE
            badge_class = block_status.lower().replace("_", "-")
            table_rows = "".join(
                "<tr>"
                f"<th>{html.escape(str(row.get('display_label', '') or ''))}</th>"
                f"<td>{html.escape(str(row.get('value_display', '') or NOT_AVAILABLE))}</td>"
                f"<td>{html.escape(str(row.get('data_quality_flag', '') or NOT_AVAILABLE))}</td>"
                "</tr>"
                for row in rows
            )
            blocks.append(
                "<section class='section'>"
                f"<h2><span>{html.escape(section_name)}</span><span class='badge {badge_class}'>{html.escape(block_status)}</span></h2>"
                "<table>"
                "<thead><tr><th>Metric</th><th>Value</th><th>Data Quality</th></tr></thead>"
                f"<tbody>{table_rows}</tbody>"
                "</table>"
                "</section>"
            )
        section_html = "".join(blocks) if blocks else (
            "<section class='section unavailable'>"
            "<h2><span>Dashboard Sections</span><span class='badge not-available'>NOT_AVAILABLE</span></h2>"
            "<p>No dashboard sections available.</p>"
            "</section>"
        )

    kpi_count = "NOT_AVAILABLE" if is_not_available(kpis) else str(len(kpis))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Compound Income OS Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f1e8;
      --panel: #fffdf7;
      --ink: #1f2430;
      --muted: #5b6472;
      --line: #d5ccb9;
      --available: #1d6f42;
      --partial: #8a5a00;
      --not-available: #8c2f39;
    }}
    body {{
      margin: 0;
      padding: 24px;
      background: linear-gradient(180deg, #ece5d3 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }}
    main {{ max-width: 1120px; margin: 0 auto; }}
    h1 {{ margin-bottom: 8px; }}
    p.meta {{ color: var(--muted); margin-top: 0; }}
    .summary, .section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px 20px;
      margin-bottom: 18px;
      box-shadow: 0 8px 24px rgba(31, 36, 48, 0.06);
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .summary-card {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      background: #fffaf0;
    }}
    .summary-label {{ font-size: 0.85rem; color: var(--muted); }}
    .summary-value {{ font-size: 1.15rem; font-weight: bold; margin-top: 4px; }}
    h2 {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 0 0 14px;
      font-size: 1.15rem;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      letter-spacing: 0.04em;
      color: #fff;
    }}
    .badge.available {{ background: var(--available); }}
    .badge.partial {{ background: var(--partial); }}
    .badge.not-available {{ background: var(--not-available); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      text-align: left;
      padding: 10px 8px;
      border-top: 1px solid var(--line);
      vertical-align: top;
    }}
    thead th {{ border-top: none; color: var(--muted); font-size: 0.9rem; }}
    footer {{ color: var(--muted); font-size: 0.9rem; padding-top: 8px; }}
  </style>
</head>
<body>
  <main>
    <h1>Compound Income OS Dashboard</h1>
    <p class="meta">Read-only localhost viewer for dashboard CSV artifacts. KPI rows loaded: {html.escape(kpi_count)}.</p>
    {render_summary_block(summary)}
    {section_html}
    <footer>Data mtime: {html.escape(data_mtime)}</footer>
  </main>
</body>
</html>
"""


class DashboardRequestHandler(BaseHTTPRequestHandler):
    server: "DashboardHTTPServer"

    def do_GET(self) -> None:  # noqa: N802
        data_mtime = latest_mtime(self.server.dashboard_paths.all_paths())
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._serve_index(data_mtime)
                return
            if parsed.path == "/api/kpis.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.kpis, load_kpis), data_mtime)
                return
            if parsed.path == "/api/sections.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.sections, load_sections), data_mtime)
                return
            if parsed.path == "/api/summary.json":
                self._serve_json(self.server.artifact_cache.get(self.server.dashboard_paths.summary, load_summary), data_mtime)
                return
            if parsed.path == "/healthz":
                self._serve_json({"status": "OK"}, data_mtime)
                return
            self._serve_json({"status": "NOT_FOUND", "path": parsed.path}, data_mtime, status_code=404)
        except Exception as exc:  # pragma: no cover - defensive HTTP path
            LOGGER.exception("dashboard_server request failed")
            self._serve_json({"status": "ERROR", "message": str(exc)}, data_mtime, status_code=500)

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)

    def _serve_index(self, data_mtime: str) -> None:
        kpis = self.server.artifact_cache.get(self.server.dashboard_paths.kpis, load_kpis)
        sections = self.server.artifact_cache.get(self.server.dashboard_paths.sections, load_sections)
        summary = self.server.artifact_cache.get(self.server.dashboard_paths.summary, load_summary)
        body = render_index_html(kpis, sections, summary, data_mtime).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", HTML_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Dashboard-Data-Mtime", data_mtime)
        self.end_headers()
        self.wfile.write(body)

    def _serve_json(self, payload: Any, data_mtime: str, status_code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", JSON_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Dashboard-Data-Mtime", data_mtime)
        self.end_headers()
        self.wfile.write(body)


class DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], paths: DashboardPaths) -> None:
        super().__init__(server_address, DashboardRequestHandler)
        self.dashboard_paths = paths
        self.artifact_cache = ArtifactCache()


def build_server(host: str, port: int, paths: DashboardPaths) -> DashboardHTTPServer:
    return DashboardHTTPServer((validate_host(host), int(port)), paths)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve dashboard CSV artifacts as a local read-only localhost UI.")
    parser.add_argument("--kpis", default=DEFAULT_KPI_OUTPUT, help="Dashboard KPI CSV.")
    parser.add_argument("--sections", default=DEFAULT_SECTIONS_OUTPUT, help="Dashboard sections CSV.")
    parser.add_argument("--summary", default=DEFAULT_SUMMARY_OUTPUT, help="Dashboard summary CSV.")
    parser.add_argument("--host", default="127.0.0.1", help="Local bind host. Only 127.0.0.1 is allowed.")
    parser.add_argument("--port", type=int, default=8765, help="Local bind port.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    host = validate_host(args.host)
    paths = DashboardPaths(kpis=args.kpis, sections=args.sections, summary=args.summary)
    server = build_server(host, args.port, paths)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    LOGGER.info("Serving dashboard on http://%s:%s", host, server.server_address[1])
    LOGGER.info("Changes to the three dashboard CSV artifacts become visible on the next request; no restart is required.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - manual stop path
        LOGGER.info("Stopping dashboard server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
