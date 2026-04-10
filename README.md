# Compound Income OS

Lokales, reproduzierbares Portfolio-Research- und Decision-Support-System fuer ein langfristiges Aktienportfolio mit dem Mandat:

`Dividend Growth + Quality Compounders mit wertorientiertem, datengetriebenem Kaufansatz`

Das System fuehrt keine Orders aus. Es verarbeitet CSV-Inputs deterministisch zu Scores, Rankings und Markdown-Reports.

## Repo-Struktur

- `configs/`: Portfolio-Regeln, Scoring-Gewichte, Watchlist-Regeln, Datenquellen
- `data/raw/`: manuelle CSV-Inputs und Fixture-Daten
- `data/processed/`: deterministische CSV-Artefakte
- `reports/`: generierte Markdown-Reports
- `research/`: Platzhalter fuer spaetere Deep-Dives
- `src/`: Kernmodule und CLI-Entry-Points
- `tests/`: `unittest`-basierte Kernlogik-Tests

## Design-Prinzipien

- Standardmaessig nur lokale CSV-Dateien
- JSON-kompatible YAML-Konfigurationen, damit kein externer YAML-Parser noetig ist
- Harte Trennung zwischen `raw`, `processed` und `reports`
- Fehlende Daten werden als `REVIEW` oder `MISSING_DATA` markiert
- Keine Auto-Trades, keine Broker-Orderlogik, keine versteckte Cash-Hardcodes

## Config-Format

- Alle `configs/*.yaml` muessen JSON-kompatibles YAML enthalten.
- Der Config-Loader nutzt bewusst `json.load()` aus der Python-Standardbibliothek und keinen externen YAML-Parser.

## Wichtige Konfiguration

Die zentrale Portfolio-Konfiguration liegt in [configs/portfolio_rules.yaml](/C:/Users/sc_mprinsen/Documents/compound_income_os/configs/portfolio_rules.yaml).

Der monatliche Cash-Zufluss ist dort ueber `monthly_new_cash_eur` konfigurierbar und wird von Ranking und Reports direkt genutzt.

## CLI-Entry-Points

```powershell
python -m src.import_broker --input data/raw/sample_portfolio.csv --output data/processed/positions_snapshot.csv
python -m src.scoring_engine --positions data/processed/positions_snapshot.csv --fundamentals data/raw/sample_fundamentals.csv --output data/processed/company_scores.csv
python -m src.watchlist_engine --input data/raw/sample_watchlist.csv --scores data/processed/company_scores.csv --output data/processed/watchlist_ranked.csv
python -m src.monthly_ranking_engine --positions data/processed/positions_snapshot.csv --scores data/processed/company_scores.csv --watchlist data/processed/watchlist_ranked.csv --output data/processed/monthly_buy_ranking.csv
python -m src.build_portfolio_snapshot --positions data/processed/positions_snapshot.csv --scores data/processed/company_scores.csv --output reports/2026-04-10/portfolio_snapshot.md
python -m src.build_monthly_decision_report --positions data/processed/positions_snapshot.csv --scores data/processed/company_scores.csv --ranking data/processed/monthly_buy_ranking.csv --output reports/2026-04-10/monthly_decision_report.md
```

Optional erzeugt `src.watchlist_engine` auch direkt einen Markdown-Report:

```powershell
python -m src.watchlist_engine --input data/raw/sample_watchlist.csv --scores data/processed/company_scores.csv --output data/processed/watchlist_ranked.csv --report-output reports/2026-04-10/watchlist_report.md
```

## Testlauf

```powershell
python -m unittest discover -s tests -v
```

## Hinweise zu Datenquellen

- Stabiler Standard: `manual_csv` / `broker_export`
- Optional spaeter: Trade-Republic-Dokumentadapter
- Optional spaeter: read-only inoffizielle API
- Kein Adapter darf Orders ausfuehren

## Phase-1-Artefakte

Die Pipeline erzeugt mindestens:

- `data/processed/positions_snapshot.csv`
- `data/processed/company_scores.csv`
- `data/processed/watchlist_ranked.csv`
- `data/processed/monthly_buy_ranking.csv`
- `data/processed/rebalance_proposals.csv`
- `reports/YYYY-MM-DD/portfolio_snapshot.md`
- `reports/YYYY-MM-DD/monthly_decision_report.md`
- `reports/YYYY-MM-DD/watchlist_report.md`
