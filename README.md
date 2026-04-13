# Compound Income OS

Lokales, reproduzierbares Portfolio-Research- und Decision-Support-System fuer ein langfristiges Aktienportfolio mit dem Mandat:

`Dividend Growth + Quality Compounders mit wertorientiertem, datengetriebenem Kaufansatz`

Das System fuehrt keine Orders aus. Es verarbeitet CSV-Inputs und lokale textbasierte Broker-PDFs deterministisch zu Scores, Rankings und Markdown-Reports.

## Repo-Struktur

- `configs/`: Portfolio-Regeln, Scoring-Gewichte, Watchlist-Regeln, Datenquellen
- `data/raw/`: manuelle CSV-Inputs und Fixture-Daten
- `data/processed/`: deterministische CSV-Artefakte
- `reports/`: generierte Markdown-Reports
- `research/`: Platzhalter fuer spaetere Deep-Dives
- `src/`: Kernmodule und CLI-Entry-Points
- `tests/`: `unittest`-basierte Kernlogik-Tests

## Project governance / canonical docs

`AGENTS.md` und `docs/` bilden die kanonische Alignment-Basis fuer kuenftige Codex-Arbeit. Governance-Dokumente muessen explizit unterscheiden zwischen getrackter HEAD-Repo-Realitaet, beobachtetem dirty/untracked local Worktree und geplantem Roadmap-Zustand.

- [AGENTS.md](AGENTS.md): kurzer operativer Einstieg und Guardrails fuer Codex
- [docs/PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md): harte Projektcharta, Scope und Invarianten
- [docs/CONTEXT_AND_ROADMAP.md](docs/CONTEXT_AND_ROADMAP.md): Ist-Zustand, lokale Worktree-Beobachtungen und Roadmap
- [docs/MODULE_CONTRACTS.md](docs/MODULE_CONTRACTS.md): Modulvertraege, Inputs, Outputs und Drift-Risiken
- [docs/CODEX_TASK_TEMPLATE.md](docs/CODEX_TASK_TEMPLATE.md): wiederverwendbares Task-Template
- [docs/CODEX_TASKS/POST_ITERATION_QA.md](docs/CODEX_TASKS/POST_ITERATION_QA.md): standardisierter Post-Iteration-QA-/Bug-Hunt-Task

## Design-Prinzipien

- Standardmaessig nur lokale CSV-Dateien und explizit angegebene lokale Dokumente
- JSON-kompatible YAML-Konfigurationen, damit kein externer YAML-Parser noetig ist
- Harte Trennung zwischen `raw`, `processed` und `reports`
- Fehlende Daten werden als `REVIEW` oder `MISSING_DATA` markiert
- Keine Auto-Trades, keine Broker-Orderlogik, keine versteckte Cash-Hardcodes
- Keine OCR-, API- oder Live-Daten-Integration im Phase-1-Pfad

## Config-Format

- Alle `configs/*.yaml` muessen JSON-kompatibles YAML enthalten.
- Der Config-Loader nutzt bewusst `json.load()` aus der Python-Standardbibliothek und keinen externen YAML-Parser.

## Wichtige Konfiguration

Die zentrale Portfolio-Konfiguration liegt in [configs/portfolio_rules.yaml](configs/portfolio_rules.yaml).

Der monatliche Cash-Zufluss ist dort ueber `monthly_new_cash_eur` konfigurierbar und wird von Ranking und Reports direkt genutzt.

Die transparente Fundamentals-Schicht liegt in:

- [configs/fundamentals_schema.yaml](configs/fundamentals_schema.yaml): erwartete Raw-KPI-Felder und Legacy-Score-Felder
- [configs/fundamentals_score_rules.yaml](configs/fundamentals_score_rules.yaml): KPI-Score-Regeln und Teil-Score-Aggregation
- [configs/scoring_weights.yaml](configs/scoring_weights.yaml): Aggregation zu Business Score, Valuation Score und Buy Score
- [configs/fundamentals_metric_definitions.yaml](configs/fundamentals_metric_definitions.yaml): KPI-Definitionen, Profil-Anwendbarkeit und Missing-Handling fuer den Personal-Master

## CLI-Entry-Points

Fixture-/Sample-Pipeline:

```powershell
python -m src.import_broker --input data/raw/sample_portfolio.csv --output data/processed/positions_snapshot.csv
python -m src.scoring_engine --positions data/processed/positions_snapshot.csv --fundamentals data/raw/sample_fundamentals.csv --output data/processed/company_scores.csv
python -m src.watchlist_engine --input data/raw/sample_watchlist.csv --scores data/processed/company_scores.csv --output data/processed/watchlist_ranked.csv
python -m src.monthly_ranking_engine --positions data/processed/positions_snapshot.csv --scores data/processed/company_scores.csv --watchlist data/processed/watchlist_ranked.csv --output data/processed/monthly_buy_ranking.csv
python -m src.build_portfolio_snapshot --positions data/processed/positions_snapshot.csv --scores data/processed/company_scores.csv --output reports/sample/portfolio_snapshot.md
python -m src.build_monthly_decision_report --positions data/processed/positions_snapshot.csv --scores data/processed/company_scores.csv --ranking data/processed/monthly_buy_ranking.csv --output reports/sample/monthly_decision_report.md
```

Transparenter Raw-Fundamentals-Lauf mit Audit-Outputs:

```powershell
python -m src.import_broker --input data/raw/sample_portfolio.csv --output data/processed/positions_snapshot.csv
python -m src.scoring_engine --positions data/processed/positions_snapshot.csv --fundamentals data/raw/sample_fundamentals_raw.csv --fundamentals-format raw --output data/processed/company_scores.csv --enriched-output data/processed/fundamentals_enriched.csv --audit-output data/processed/score_audit.csv
```

Optional erzeugt `src.watchlist_engine` auch direkt einen Markdown-Report:

```powershell
python -m src.watchlist_engine --input data/raw/sample_watchlist.csv --scores data/processed/company_scores.csv --output data/processed/watchlist_ranked.csv --report-output reports/sample/watchlist_report.md
```

Die Ausgabeordner unter `reports/` sind frei waehlbar. Fuer datierte Laeufe kann z. B. `reports/YYYY-MM-DD/` verwendet werden.

## Real-Depot-Onboarding

Fuer echte Depot-CSV-Dateien gibt es einen separaten, aber kompatiblen Importpfad:

```powershell
python -m src.import_broker --input data/raw/real_portfolio_example.csv --output data/processed/real_positions_snapshot.csv --mode real --source-name manual_real_depot
python -m src.scoring_engine --positions data/processed/real_positions_snapshot.csv --fundamentals data/raw/sample_fundamentals.csv --output data/processed/real_company_scores.csv
python -m src.build_portfolio_snapshot --positions data/processed/real_positions_snapshot.csv --scores data/processed/real_company_scores.csv --holdings-output data/processed/portfolio_holdings_action_table.csv --output reports/sample/real_portfolio_review.md
```

Der Real-Import akzeptiert flexible Spalten-Aliases, unter anderem fuer:

- `name` / `instrument` / `security_name`
- `ticker` / `symbol`
- `isin`
- `quantity` / `shares` / `units`
- `market_value` / `current_value`
- `avg_price` / `purchase_price`
- `current_price` / `price`
- `asset_type` / `category` / `position_type`
- `cash`

Der interne Snapshot haelt dabei u. a. `portfolio_date`, `source_name`, `raw_name`, `ticker`, `isin`, `asset_type`, `sleeve`, `current_price`, `avg_cost`, `market_value`, `mandate_fit`, `data_quality_flag` und `review_flag`.

Unvollstaendige oder problematische Bestandszeilen werden nicht glattgebuegelt:

- fehlende oder unklare Identifier fuehren zu `REVIEW` oder `MISSING_DATA`
- NON_CORE-/Legacy-Positionen bleiben sichtbar
- fehlende Fundamentals werden spaeter im Scoring konservativ degradiert statt aufgefuellt

## Fundamentals und Score-Audit

Es gibt drei unterstuetzte Fundamentals-Formate:

- Legacy: `data/raw/sample_fundamentals.csv` enthaelt voraggregierte Teil-Scores wie `quality_score`, `dividend_score`, `balance_sheet_score`, `growth_quality_score` und `capital_allocation_score`.
- Raw: `data/raw/sample_fundamentals_raw.csv` enthaelt Roh-KPIs wie `roic`, `roce`, Margen, Wachstumsraten, Verschuldung, Dividenden- und Bewertungskennzahlen. Die Teil-Scores werden daraus deterministisch abgeleitet.
- Personal: `data/raw/personal_fundamentals_master.csv` ist die lokale Source of Truth fuer reale persoenliche Holdings. Diese Datei darf keine Sample-Werte still uebernehmen; nicht recherchierte KPIs bleiben leer und werden als Coverage-/Research-Luecken ausgewiesen.

Bei `--fundamentals-format auto` bleibt ein Legacy-Input mit alten Bewertungsfeldern Legacy-kompatibel. Sobald Raw-Komponenten-KPIs wie `roic`, `roce`, Margen, Bilanz-, Wachstums- oder Kapitalallokationsfelder befuellt sind, wird der Datensatz als Raw behandelt und gegen `configs/fundamentals_schema.yaml` validiert. Wenn der Input `personal_fundamentals_master.csv` heisst oder `--fundamentals-format personal` gesetzt ist, wird der Personal-Master-Pfad genutzt.

Phase 2A nutzt fuer Raw-Fundamentals diese Score-Ableitung:

- `quality_score`: `roic`, `roce`, `gross_margin`, `operating_margin`, `fcf_margin`
- `dividend_score`: `dividend_yield_current_pct`, `dividend_yield_hist_pct`, `dividend_cagr_5y`, `dividend_streak_years`, `payout_ratio_eps`, `payout_ratio_fcf`
- `balance_sheet_score`: `net_debt_to_ebitda`, `interest_coverage`
- `growth_quality_score`: `revenue_cagr_5y`, `eps_cagr_5y`, `fcf_per_share_cagr_5y`
- `capital_allocation_score`: `share_count_cagr_5y`, `buyback_yield`

Fehlende KPI-Werte werden nicht erfunden. Je nach Umfang der Luecken werden Fundamentals-Zeilen als `REVIEW` oder `MISSING_DATA` markiert und mit konservativen Fallback-Scores verarbeitet.

Der Personal-Master trennt Core-Fundamentals von Overlay-Feldern:

- Core-Fundamentals sind Roh-KPIs wie `roic`, `roce`, `fcf_margin`, `net_debt_to_ebitda`, `interest_coverage`, `payout_ratio_fcf`, `share_count_cagr_5y`, `buyback_yield`, `normalized_fcf_yield_pct` und `target_fcf_yield_pct`.
- Overlay-Felder tragen bewusst den Praefix `overlay_`, z. B. `overlay_thesis_robustness`, `overlay_has_hard_risk_flag`, `overlay_analyst_notes`, `overlay_manual_override_flag` und `overlay_manual_override_reason`.
- `company_type_profile` ist verpflichtend im Master und unterstuetzt `STANDARD`, `FINANCIAL`, `REIT` und `OTHER`. Standard-KPIs werden nur fuer Profile als Pflichtluecke gezaehlt, fuer die sie laut `configs/fundamentals_metric_definitions.yaml` anwendbar sind.

Das konservative Matching fuer persoenliche Holdings ist deterministisch:

1. ISIN exact match
2. Ticker exact match
3. Normalisierter `company_name` exact match
4. Sonst `NO_MATCH`

Mehrdeutige Treffer werden nicht geraten, sondern als `REVIEW` mit `match_conflict_flag=True` ausgewiesen. Coverage-Kategorien sind `COVERED`, `PARTIAL`, `REVIEW` und `NO_MATCH`; echte Pflichtluecken erscheinen separat in `missing_required_kpis`, nicht anwendbare KPIs in `not_applicable_kpis`.

Der Audit-Output `data/processed/score_audit.csv` zeigt pro Titel:

- verwendete Raw-KPIs
- abgeleitete Teil-Scores
- Valuation-Zwischengroessen wie `pe_relative_ratio`, `ev_ebit_relative_ratio`, `fcf_yield_relative_ratio`, `normalized_fcf_gap`
- Buy-Score-Komponenten wie `business_score_contribution`, `valuation_score_contribution`, `expected_return_score_contribution`, `drawdown_score_contribution`, `portfolio_fit_score_contribution`
- Datenqualitaetsflags und fehlende KPI-Felder

Benchmarking, Kosten-/Steuer-Tracking und Dashboard sind nicht Teil von Phase 2A.

## Phase 2B Performance und Benchmark

Phase 2B fuehrt eine lokale, deterministische Benchmark-/Performance-Schicht ein, ohne die bestehenden Phase-1/2A-Pfade umzubauen.

Wichtige Abgrenzung:

- Snapshot-Performance basiert direkt auf dem aktuellen `positions_snapshot.csv` und liefert nur aktuelle NAV-/Gewichtungs-KPIs.
- Historische Performance wird nur berechnet, wenn eine explizite datierte Portfolio-Zeitreihe mit `date` und `portfolio_nav_eur` vorliegt.
- Eine explizite Portfolio-Zeitreihe darf nicht nach dem Snapshot-Stichtag enden; spaetere Endpunkte werden hart abgewiesen.
- `avg_cost`, `cost_basis_eur` und `unrealized_pnl_eur` ersetzen keine historische Performance-Zeitreihe.
- Kosten, Steuern, FX-Konvertierung, TWR und IRR sind nicht Teil von Phase 2B.

Verfuegbare Datenmodi:

- `SNAPSHOT_ONLY`: nur ein belastbarer Portfolio-Zeitpunkt, keine Periodenrendite, keine Drawdown-/Volatilitaetsmetriken
- `PARTIAL_HISTORY`: mindestens zwei explizite Portfolio-Zeitpunkte, einfacher Periodenvergleich moeglich
- `FULL_HISTORY`: weitergehende Historienmetriken erst bei ausreichend expliziter Historie; Phase 2B markiert fehlende Tiefe ansonsten als `INSUFFICIENT_HISTORY`

Methodenlabels:

- `SNAPSHOT_COMPARISON`
- `SIMPLE_PERIOD_RETURN`

Benchmark-Konfiguration und CSV-Schema:

- `configs/benchmark.yaml` ist JSON-kompatibles YAML und wird via `json.load()` gelesen.
- Erwartete Kernspalten in der Benchmark-CSV: `date`, `benchmark_name`, `benchmark_symbol`, `close`
- Optional: `adjusted_close`, `total_return_index`, `dividend`, `source_name`, `currency`
- Return-Basis-Prioritaet: `total_return_index` > `adjusted_close` > `close`
- Die global gewaehlte Return-Basis muss in allen Benchmark-Zeilen befuellt sein; leere Spaetzeilen werden hart abgewiesen statt still als `0.0` zu laufen.
- Falls nur `close` vorhanden ist, wird die Benchmark weiter genutzt, aber mit dem Flag `APPROX_PRICE_ONLY_BENCHMARK`
- Ohne FX-Layer wird bei Waehrungsabweichung explizit `CURRENCY_MISMATCH` gesetzt
- Wenn der letzte verwendbare Benchmark-Punkt gegenueber dem Portfolio-as-of um mindestens 2 Kalendertage hinterherhaengt, wird der Lauf nicht hart abgebrochen, aber explizit als `STALE_BENCHMARK` markiert.

Neue Artefakte:

- `data/processed/benchmark_timeseries_normalized.csv`
- `data/processed/portfolio_timeseries.csv`
- `data/processed/performance_summary.csv`
- `data/processed/performance_comparison.csv`
- `data/processed/performance_kpis.csv`
- `reports/YYYY-MM-DD/performance_report.md`

Snapshot-Only-Beispiel:

```powershell
python -m src.performance_engine --positions data/processed/personal_positions_snapshot.csv --benchmark data/raw/sample_benchmark_timeseries.csv --benchmark-config configs/benchmark.yaml --comparison-output data/processed/performance_comparison.csv --kpi-output data/processed/performance_kpis.csv --report-output reports/sample/performance_report.md
```

Optionaler Periodenvergleich mit expliziter NAV-Zeitreihe:

```powershell
python -m src.performance_engine --positions data/processed/personal_positions_snapshot.csv --portfolio-timeseries data/raw/portfolio_timeseries.csv --benchmark data/raw/sample_benchmark_timeseries.csv --benchmark-config configs/benchmark.yaml --comparison-output data/processed/performance_comparison.csv --kpi-output data/processed/performance_kpis.csv --report-output reports/sample/performance_report.md
```

## Phase 2C Cost and Tax Ledger

Phase 2C fuehrt eine lokale, deterministische Cost-/Tax-Ledger-Schicht ein. Der primaere Pfad ist ein manueller CSV-Ledger; Dokumentparser bleiben optional und bewusst eng begrenzt.

Measurement Modes:

- `DOCUMENT_SUMMARY_ONLY`: nur aggregierte Dokument-/Periodensummen, keine vollstaendige Event-Abdeckung
- `PARTIAL_LEDGER`: einzelne Events oder partielle CSV-/Dokumentsummen, aber keine vollstaendige belastbare Event-Abdeckung
- `FULL_LEDGER`: ausreichend explizite `EVENT`-Zeilen mit `verification_status=VERIFIED` und sauberer Datenqualitaet

Pflichttrennung im Ledger:

- `record_granularity`: `EVENT`, `DOCUMENT_SUMMARY`, `PERIOD_SUMMARY`
- `verification_status`: `VERIFIED`, `PARTIAL`, `UNVERIFIED`, `REVIEW`

Erwartetes Ledger-CSV-Schema:

- Kernspalten: `event_date`, `broker`, `document_type`, `record_granularity`, `event_type`, `instrument_name`, `ticker`, `isin`, `currency`, `gross_amount`, `net_amount`, `fee_amount`, `tax_amount`, `withholding_tax_amount`, `quantity`, `price_per_unit`, `reference_id`, `source_name`, `verification_status`, `data_quality_flag`, `notes`
- Wichtige optionale Felder: `event_group_id`, `document_period_start`, `document_period_end`, `realized_proceeds_amount`, `realized_cost_basis_amount`, `realized_pnl_before_tax`, `realized_pnl_after_tax_estimate_or_partial`, `tax_jurisdiction`

Aktuell real unterstuetzte Dokumenttypen:

- `Depotauszug.pdf`: nur Holdings-Snapshot, kein Trade-/Tax-Ledger
- `Kontoauszug.pdf`: nur Cash-Endsaldo, kein vollstaendiges Event-Ledger
- optional begrenzte Trade-Republic-Jahressteuerbescheinigungen `Steuerbericht` / `Steuerreport`: nur dokumentierte Summary-Totals, kein universeller Parser

Methodische Leitplanken:

- `avg_cost`, `cost_basis_eur` und `unrealized_pnl_eur` aus dem Snapshot ersetzen kein steuerliches Event-Ledger
- Realized PnL wird nur bei expliziter Evidenz ausgewiesen, z. B. ueber `realized_proceeds_amount`, `realized_cost_basis_amount` oder `realized_pnl_before_tax`
- Netto-/Steuerkennzahlen werden nur soweit berechnet, wie der Ledger oder ein expliziter Dokument-Summary-Wert sie real traegt
- Dashboard, erweiterte Steuerlogik, Lot-Rekonstruktion und automatische FIFO-/Average-Cost-Modelle sind nicht Teil von Phase 2C

Neue Artefakte:

- `data/processed/cost_tax_ledger_normalized.csv`
- `data/processed/cost_tax_summary.csv`
- `data/processed/cost_tax_kpis.csv`
- `reports/YYYY-MM-DD/cost_tax_report.md`

Sample-CLI:

```powershell
python -m src.cost_tax_engine --ledger data/raw/sample_cost_tax_ledger.csv --summary-output data/processed/cost_tax_summary.csv --kpi-output data/processed/cost_tax_kpis.csv --report-output reports/sample/cost_tax_report.md
```

## Phase 2D KPI-Dashboard

Phase 2D ist eine Konsolidierungs- und Reporting-Schicht. Sie baut keine neue Bewertungs-, Performance- oder Steuerlogik, sondern liest strukturierte CSV-Artefakte aus Phase 1/2A/2B/2C ein und konsolidiert sie zu einem operativen Dashboard.

Primaerquellen:

- Portfolio / Struktur: `positions_snapshot.csv`
- Score / Fundamentals: `company_scores.csv`, `portfolio_holdings_action_table.csv`, optional `score_audit.csv` und `personal_fundamentals_coverage.csv`
- Benchmark / Performance: `performance_kpis.csv`, `performance_summary.csv`, optional `performance_comparison.csv`
- Kosten / Steuern: `cost_tax_kpis.csv`, `cost_tax_summary.csv`

Wichtige Leitplanken:

- Markdown-Reports sind nicht die primaere KPI-Quelle.
- Fehlende Inputs werden nicht mit `0` aufgefuellt, sondern als `NOT_AVAILABLE` oder `INSUFFICIENT_HISTORY` markiert.
- Blockstatus werden explizit als `AVAILABLE`, `PARTIAL` oder `NOT_AVAILABLE` ausgewiesen.
- Measurement Modes wie `SNAPSHOT_ONLY`, `PARTIAL_HISTORY`, `FULL_LEDGER` und `DOCUMENT_SUMMARY_ONLY` werden aus den vorhandenen Artefakten uebernommen, nicht neu erfunden.
- KPI-Dateiquellen mit `metric_name` muessen eindeutige, nicht-leere Werte haben; doppelte oder leere Namen werden hart abgewiesen.
- Das Dashboard prueft Snapshot-, Performance- und Cost-/Tax-Stichtage gegeneinander und markiert veraltete Upstream-Quellen explizit, statt sie still als aktuell zu behandeln.
- Das Dashboard ist bewusst keine neue Performance-, Score- oder Steuerquelle.

Neue Artefakte:

- `data/processed/dashboard_kpis.csv`
- `data/processed/dashboard_sections.csv`
- `data/processed/dashboard_summary.csv`
- `reports/YYYY-MM-DD/dashboard_report.md`

Sample-CLI:

```powershell
python -m src.dashboard_engine --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --holdings data/processed/personal_portfolio_holdings_action_table.csv --score-audit data/processed/personal_score_audit.csv --coverage data/processed/personal_fundamentals_coverage.csv --performance-kpis data/processed/performance_kpis.csv --performance-summary data/processed/performance_summary.csv --performance-comparison data/processed/performance_comparison.csv --cost-tax-kpis data/processed/cost_tax_kpis.csv --cost-tax-summary data/processed/cost_tax_summary.csv --config configs/dashboard_kpis.yaml --kpi-output data/processed/dashboard_kpis.csv --sections-output data/processed/dashboard_sections.csv --summary-output data/processed/dashboard_summary.csv --report-output reports/sample/dashboard_report.md
```

## Persoenlicher Lauf

Der persoenliche Lauf kann entweder ueber einen manuellen CSV-Depotexport oder ueber offizielle textbasierte Trade-Republic-Dokumente erfolgen. Der PDF-Pfad nutzt lokal nur `data/raw/private/traderepublic/Depotauszug.pdf` fuer Holdings und `data/raw/private/traderepublic/Kontoauszug.pdf` fuer den Cash-Endsaldo.

Empfohlener persoenlicher CSV-Lauf:

```powershell
python -m src.import_broker --input data/raw/personal_depot.csv --output data/processed/personal_positions_snapshot.csv --mode real --source-name personal_depot
python -m src.fundamentals_master --positions data/processed/personal_positions_snapshot.csv --init-master-output data/raw/personal_fundamentals_master.csv
python -m src.scoring_engine --positions data/processed/personal_positions_snapshot.csv --fundamentals data/raw/personal_fundamentals_master.csv --fundamentals-format personal --output data/processed/personal_company_scores.csv --audit-output data/processed/personal_score_audit.csv
python -m src.fundamentals_master --positions data/processed/personal_positions_snapshot.csv --fundamentals data/raw/personal_fundamentals_master.csv --scores data/processed/personal_company_scores.csv --coverage-output data/processed/personal_fundamentals_coverage.csv --enriched-output data/processed/personal_fundamentals_enriched.csv --report-output reports/YYYY-MM-DD/personal_fundamentals_coverage_report.md
python -m src.watchlist_engine --input data/raw/sample_watchlist.csv --scores data/processed/personal_company_scores.csv --output data/processed/personal_watchlist_ranked.csv --report-output reports/sample/personal_watchlist_report.md
python -m src.monthly_ranking_engine --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --watchlist data/processed/personal_watchlist_ranked.csv --output data/processed/personal_monthly_buy_ranking.csv --rebalance-output data/processed/personal_rebalance_proposals.csv
python -m src.build_monthly_decision_report --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --ranking data/processed/personal_monthly_buy_ranking.csv --coverage data/processed/personal_fundamentals_coverage.csv --output reports/sample/personal_monthly_decision_report.md
python -m src.build_portfolio_snapshot --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --coverage data/processed/personal_fundamentals_coverage.csv --holdings-output data/processed/personal_portfolio_holdings_action_table.csv --output reports/sample/personal_portfolio_review.md
```

Empfohlener persoenlicher Trade-Republic-PDF-Lauf:

```powershell
python -m src.import_broker --input data/raw/private/traderepublic/Depotauszug.pdf --cash-input data/raw/private/traderepublic/Kontoauszug.pdf --output data/processed/personal_positions_snapshot.csv --mode tr_pdf --source-name trade_republic_official_docs
python -m src.fundamentals_master --positions data/processed/personal_positions_snapshot.csv --init-master-output data/raw/personal_fundamentals_master.csv
python -m src.scoring_engine --positions data/processed/personal_positions_snapshot.csv --fundamentals data/raw/personal_fundamentals_master.csv --fundamentals-format personal --output data/processed/personal_company_scores.csv --audit-output data/processed/personal_score_audit.csv
python -m src.fundamentals_master --positions data/processed/personal_positions_snapshot.csv --fundamentals data/raw/personal_fundamentals_master.csv --scores data/processed/personal_company_scores.csv --coverage-output data/processed/personal_fundamentals_coverage.csv --enriched-output data/processed/personal_fundamentals_enriched.csv --report-output reports/YYYY-MM-DD/personal_fundamentals_coverage_report.md
python -m src.watchlist_engine --input data/raw/sample_watchlist.csv --scores data/processed/personal_company_scores.csv --output data/processed/personal_watchlist_ranked.csv --report-output reports/sample/personal_watchlist_report.md
python -m src.monthly_ranking_engine --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --watchlist data/processed/personal_watchlist_ranked.csv --output data/processed/personal_monthly_buy_ranking.csv --rebalance-output data/processed/personal_rebalance_proposals.csv
python -m src.build_monthly_decision_report --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --ranking data/processed/personal_monthly_buy_ranking.csv --coverage data/processed/personal_fundamentals_coverage.csv --output reports/sample/personal_monthly_decision_report.md
python -m src.build_portfolio_snapshot --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --coverage data/processed/personal_fundamentals_coverage.csv --holdings-output data/processed/personal_portfolio_holdings_action_table.csv --output reports/sample/personal_portfolio_review.md
```

Interpretation der persoenlichen Outputs:

- `personal_positions_snapshot.csv`: normalisierte Bestandsdaten aus dem privaten Depotexport
- `personal_fundamentals_master.csv`: lokale Source of Truth fuer persoenliche Fundamentals; initiale Seed-Zeilen aus dem Snapshot enthalten nur Identitaet und muessen manuell mit belegten KPIs ergaenzt werden
- `personal_company_scores.csv`: Score- und Bewertungsdaten fuer die persoenlichen Holdings, bevorzugt aus dem Personal-Master statt aus Sample-Fundamentals
- `personal_score_audit.csv`: nachvollziehbare KPI-/Teilscore-/Buy-Score-Auditspur mit `fundamentals_input_format`
- `personal_fundamentals_coverage.csv`: Match- und Coverage-Status je Holding inklusive `missing_required_kpis`, `not_applicable_kpis` und `needs_research_flag`
- `personal_fundamentals_enriched.csv`: gematchte Holdings mit Master-Roh-KPIs, bestehenden Teil-Scores und Source-Metadaten
- `personal_fundamentals_coverage_report.md`: Markdown-Report mit COVERED/PARTIAL/REVIEW/NO_MATCH und Research-Luecken
- `personal_portfolio_holdings_action_table.csv`: operative Holdings-Aktionen `ADD`, `HOLD`, `WATCH`, `REDUCE`, `EXIT_REVIEW`; bei uebergebener Coverage werden offene Fundamentals-Luecken konservativ als Guardrail sichtbar
- `personal_monthly_buy_ranking.csv`: Kauf-Ranking fuer den konfigurierten Monatszufluss
- `personal_monthly_decision_report.md`: monatlicher Entscheidungsreport mit optional eingeblendeten Fundamentals-Research-Luecken
- `personal_portfolio_review.md`: deutscher Review-Report fuer das persoenliche Depot

Datenschutz:

- Private Rohdaten sollten nicht committed werden.
- Fuer persoenliche Dateien sind z. B. `data/raw/personal_depot.csv`, `data/raw/private_depot.csv` oder `data/raw/private/traderepublic/` vorgesehen und via `.gitignore` ausgeschlossen.
- Der Trade-Republic-PDF-Pfad nutzt nur textbasierte lokale Extraktion; es wird keine OCR, API oder Umsatzhistorienmodellierung verwendet.
- Wenn im privaten Export Fundamentals oder saubere Identifier fehlen, bleiben die betreffenden Positionen offen als `REVIEW` oder `MISSING_DATA` markiert.
- ZIP- oder externe Exporte sollten nie aus dem vollen Arbeitsverzeichnis mit privaten Rohdaten erstellt werden. Fuer Teilen/Review nur Code und Sample-Daten exportieren oder private Rohdaten vorher entfernen.
- Falls private Rohdaten bereits historisch committed wurden, reicht `.gitignore` nicht; dann muss die Git-Historie separat bereinigt werden.

## Testlauf

```powershell
python -m unittest discover -s tests -v
```

## Hinweise zu Datenquellen

- Stabiler Standard: `manual_csv` / `broker_export`
- Lokal implementiert: begrenzter Trade-Republic-Dokumentadapter fuer `Depotauszug.pdf` und Cash-Endsaldo aus `Kontoauszug.pdf`
- Optional spaeter: read-only inoffizielle API
- Kein Adapter darf Orders ausfuehren

## Phase-1-Artefakte

Die Pipeline erzeugt mindestens:

- `data/processed/positions_snapshot.csv`
- `data/processed/company_scores.csv`
- `data/processed/watchlist_ranked.csv`
- `data/processed/monthly_buy_ranking.csv`
- `data/processed/rebalance_proposals.csv`
- `data/processed/real_positions_snapshot.csv`
- `data/processed/real_company_scores.csv`
- `data/processed/portfolio_holdings_action_table.csv`
- `reports/YYYY-MM-DD/portfolio_snapshot.md`
- `reports/YYYY-MM-DD/real_portfolio_review.md`
- `reports/YYYY-MM-DD/monthly_decision_report.md`
- `reports/YYYY-MM-DD/watchlist_report.md`
