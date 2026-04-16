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

`company_type_profile=OTHER` bleibt zulaessig, muss fuer `asset_type=STOCK` aber begruendet werden. Der Coverage-Pfad markiert unbegruendete `OTHER`-Profile ueber `profile_classification_warning_flag`; eine Begruendung kann im Master z. B. in `notes` als `company_type_profile_reason=...` stehen. Mit `--research-priority-output data/processed/personal_research_priority.csv` entsteht eine nach `market_value_eur`, Pflicht-KPI-Luecken und stabilen Identifiern sortierte Nachpflege-Liste. Sie ist nur eine operative Research-Hilfe und aendert keine Scores.

## Fundamentals Evidence / Research Backlog

`src.fundamentals_evidence_engine` ergaenzt den Personal-Master um eine explizite, lokale Evidence-Schicht. Der manuelle Input `data/raw/personal_fundamentals_evidence.csv` wird validiert, normalisiert und zu `data/processed/personal_fundamentals_evidence_registry.csv`, `data/processed/personal_fundamentals_research_backlog.csv`, `data/processed/personal_fundamentals_proposed_updates.csv`, optionaler Summary und einem Evidence-Report verarbeitet.

```powershell
python -m src.fundamentals_evidence_engine --fundamentals-master data/raw/personal_fundamentals_master.csv --evidence-input data/raw/personal_fundamentals_evidence.csv --metric-definitions configs/fundamentals_metric_definitions.yaml --registry-output data/processed/personal_fundamentals_evidence_registry.csv --backlog-output data/processed/personal_fundamentals_research_backlog.csv --proposed-updates-output data/processed/personal_fundamentals_proposed_updates.csv --summary-output data/processed/personal_fundamentals_evidence_summary.csv --report-output reports/YYYY-MM-DD/personal_fundamentals_evidence_report.md --template-output data/raw/personal_fundamentals_evidence_template.csv
```

Leitplanken:

- Die Evidence-Schicht nutzt dieselbe `company_type_profile`-/Required-KPI-Methodik wie `src.fundamentals_master`.
- `kpi_name` muss exakt einem kanonischen KPI aus `configs/fundamentals_metric_definitions.yaml` entsprechen; es gibt keine KPI-Aliase oder fuzzy Matches.
- Holding-Zuordnung erfolgt nur ueber exakte Ticker-/ISIN-Identitaet gegen den Personal-Master.
- `reported_value` bleibt Evidence-Metadatum und befuellt weder automatisch den Personal-Master noch Scores.
- `personal_fundamentals_proposed_updates.csv` enthaelt nur validierte Evidence-Zeilen mit `reported_value` und ist ein manueller Pruef-/Uebertragungsoutput; er schreibt nicht in den Master zurueck.
- Es gibt keine PDF-/Web-/API-Extraktion, keine automatische Rueckschreibung und keine Scoring-Aenderung.
- Ein header-only Evidence-Input ist zulaessig; bei `OTHER`-Profilen fuehrt das typischerweise zu `LOW`-Backlog statt `HIGH`, weil STANDARD-Required-KPIs fuer dieses Profil nicht als Pflichtluecke gelten.

## Fundamentals Profile Review / Profiled Master

`src.fundamentals_profile_engine` ergaenzt den Personal-Master um eine kleine, kontrollierte Pflege-Schicht nur fuer `company_type_profile`. Der manuelle Input `data/raw/personal_fundamentals_profile_review.csv` wird gegen den bestehenden Personal-Master identitaetsbasiert validiert und zu `data/processed/personal_fundamentals_profile_registry.csv`, `data/processed/personal_fundamentals_profile_review_backlog.csv` und `data/processed/personal_fundamentals_master_profiled.csv` verarbeitet.

```powershell
python -m src.fundamentals_profile_engine --fundamentals-master data/raw/personal_fundamentals_master.csv --profile-review-input data/raw/personal_fundamentals_profile_review.csv --registry-output data/processed/personal_fundamentals_profile_registry.csv --backlog-output data/processed/personal_fundamentals_profile_review_backlog.csv --profiled-master-output data/processed/personal_fundamentals_master_profiled.csv --template-output data/raw/personal_fundamentals_profile_review_template.csv
```

Leitplanken:

- Profile Review ist keine zweite Required-/Coverage-/Research-Priority-Logik. Die Methodik fuer KPI-Anwendbarkeit und Guardrails bleibt in `src.fundamentals_master`.
- Evidence = KPI-Fakten, Overlay = qualitative Analystenebene, Profile Review = kontrollierte Pflege von `company_type_profile`.
- Es gibt keine automatische Rueckschreibung in `data/raw/personal_fundamentals_master.csv`.
- Nur `APPROVED`-Reviews werden in `personal_fundamentals_master_profiled.csv` projiziert; `PENDING` und `REJECTED` bleiben in Registry und Backlog sichtbar.
- Die Projektion aendert nur `company_type_profile` plus einen nachvollziehbaren Notes-Hinweis; KPI-Werte, Overlays und andere Master-Felder bleiben unberuehrt.
- In diesem Patch nutzen Downstream-Stages den profiled Master nicht automatisch. Erst `src.personal_run_engine --use-profiled-master` schaltet geeignete fundamentals-abhaengige Stages explizit auf `personal_fundamentals_master_profiled.csv`.

## Lokaler Fundamentals Snapshot Ingest

`src.fundamentals_snapshot_ingestion` schliesst die groesste reale Datenbeschaffungsluecke im Personal-Fundamentals-Pfad: lokale externe CSV-Snapshots koennen read-only ingestiert, gegen den bestehenden Personal-Master exakt gematcht und in ein Evidence-Staging-Artefakt ueberfuehrt werden. Der Snapshot-Import ist bewusst vendor-neutral, lokal und reproduzierbar; es gibt keine Live-API, kein Web-Scraping und keine automatische Rueckschreibung in Raw-Master oder manuelle Evidence-CSV. Im Orchestrator wird derselbe Input optional ueber den Personal-Source-Key `fundamentals_snapshot_input` aufgeloest.

```powershell
python -m src.fundamentals_snapshot_ingestion --fundamentals-master data/raw/personal_fundamentals_master.csv --snapshot-input data/raw/private/fundamentals/personal_fundamentals_snapshot.csv --normalized-output data/processed/personal_fundamentals_snapshot_normalized.csv --unmatched-output data/processed/personal_fundamentals_snapshot_unmatched.csv --evidence-staging-output data/processed/personal_fundamentals_snapshot_evidence_staging.csv --summary-output data/processed/personal_fundamentals_snapshot_summary.csv --template-output data/raw/personal_fundamentals_snapshot_template.csv
```

Template- und Output-Vertrag:

- `data/raw/personal_fundamentals_snapshot_template.csv`: vendor-neutrales lokales Snapshot-Template mit exakten Identity-/Metadatenfeldern und bestehenden Core-KPI-Namen
- `data/processed/personal_fundamentals_snapshot_normalized.csv`: gematchte Snapshot-Zeilen pro Personal-Master-Identitaet
- `data/processed/personal_fundamentals_snapshot_unmatched.csv`: Snapshot-Zeilen ohne exakten Match; keine stille Holding-Erfindung
- `data/processed/personal_fundamentals_snapshot_evidence_staging.csv`: flaches Langformat im bestehenden Evidence-Eingabevertrag
- `data/processed/personal_fundamentals_snapshot_summary.csv`: reine Ingest-/Match-/Staging-Zusammenfassung

Leitplanken:

- Matchen erfolgt konservativ nur ueber exakte `ticker`-/`isin`-Identitaet gegen den bestehenden Personal-Master; `company_name` wird nicht fuzzy verwendet.
- Snapshot-Ingest erzeugt nur Staging-Evidence mit `source_type=SNAPSHOT_IMPORT`, `verification_status=UNVERIFIED` und `data_quality_flag=REVIEW`.
- Es gibt keine automatische Uebernahme in `data/raw/personal_fundamentals_evidence.csv` und keine automatische Nutzung in `scoring` oder `coverage`.
- Snapshot-Ingest ist bewusst nicht die Evidence-Engine: `src.fundamentals_evidence_engine` validiert explizite Evidence-Zeilen, Registry, Backlog und Proposed Updates; `src.fundamentals_snapshot_ingestion` bereitet nur lokale Snapshot-Exporte fuer diesen spaeteren Schritt vor.

## Snapshot Review / Promote

`src.fundamentals_snapshot_review` schliesst die operative Luecke zwischen Snapshot-Staging und validierter Evidence: einzelne Zeilen aus `personal_fundamentals_snapshot_evidence_staging.csv` koennen ueber einen separaten manuellen Review-Input explizit freigegeben, abgelehnt oder offengehalten werden. Das Ergebnis ist ein separates, auditierbares Promote-Artefakt; es gibt weiterhin keinen automatischen Merge in `data/raw/personal_fundamentals_evidence.csv` und keine automatische Rueckschreibung in den Personal-Master.

```powershell
python -m src.fundamentals_snapshot_review --staging-input data/processed/personal_fundamentals_snapshot_evidence_staging.csv --review-input data/raw/personal_fundamentals_snapshot_review.csv --registry-output data/processed/personal_fundamentals_snapshot_review_registry.csv --promoted-output data/processed/personal_fundamentals_snapshot_evidence_promoted.csv --backlog-output data/processed/personal_fundamentals_snapshot_review_backlog.csv --summary-output data/processed/personal_fundamentals_snapshot_review_summary.csv --template-output data/raw/personal_fundamentals_snapshot_review_template.csv
```

Template- und Output-Vertrag:

- `data/raw/personal_fundamentals_snapshot_review.csv`: expliziter manueller Review-Input fuer Snapshot-Staging-Zeilen
- `data/raw/personal_fundamentals_snapshot_review_template.csv`: repo-portables Header-Only-Template fuer denselben Contract
- `data/processed/personal_fundamentals_snapshot_review_registry.csv`: normalisierte Review-Entscheidungen je exakt gematchter Staging-Identitaet
- `data/processed/personal_fundamentals_snapshot_evidence_promoted.csv`: freigegebene Evidence-Zeilen im bestehenden Evidence-Eingabevertrag
- `data/processed/personal_fundamentals_snapshot_review_backlog.csv`: offene Snapshot-Review-Faelle ohne Review oder mit `PENDING`
- `data/processed/personal_fundamentals_snapshot_review_summary.csv`: reine Review-/Promote-Zusammenfassung

Leitplanken:

- Review-Matching erfolgt konservativ nur ueber exakte Staging-Identitaet; es gibt kein fuzzy Matching und keine Promotion fuer nicht existente Staging-Zeilen.
- `APPROVE` erzeugt promoted Evidence, `REJECT` und `PENDING` nicht.
- Promoted Snapshot-Evidence bleibt bewusst konservativ und erhaelt den bestehenden Snapshot-Contract; insbesondere gibt es keine stillschweigende Hochstufung auf `VERIFIED`.
- Snapshot-Review ist nicht die Evidence-Engine: `src.fundamentals_evidence_engine` bleibt der bestehende Workflow fuer validierte Evidence-Registry, Backlog und Proposed Updates.

## Evidence Compose / Explicit Evidence Switch

`src.fundamentals_evidence_compose` schliesst die operative Luecke zwischen manuell gepflegter Raw-Evidence und separater promoted Snapshot-Evidence: `data/raw/personal_fundamentals_evidence.csv` und `personal_fundamentals_snapshot_evidence_promoted.csv` koennen explizit in ein separates, auditierbares Compose-Artefakt zusammengefuehrt werden. Das Ergebnis bleibt bewusst getrennt vom Raw-Evidence-Input; es gibt kein automatisches Ueberschreiben von `data/raw/personal_fundamentals_evidence.csv`, keine Master-Rueckschreibung und keine stille Konfliktaufloesung.

```powershell
python -m src.fundamentals_evidence_compose --manual-evidence-input data/raw/personal_fundamentals_evidence.csv --promoted-evidence-input data/processed/personal_fundamentals_snapshot_evidence_promoted.csv --composed-output data/processed/personal_fundamentals_evidence_composed.csv --conflicts-output data/processed/personal_fundamentals_evidence_compose_conflicts.csv --summary-output data/processed/personal_fundamentals_evidence_compose_summary.csv
```

Leitplanken:

- Compose nutzt exakt den bestehenden Evidence-Input-Vertrag; Schema-Drift wird fail-fast abgewiesen.
- Identische Zeilen werden dedupliziert, echte Inhaltskonflikte werden in `personal_fundamentals_evidence_compose_conflicts.csv` sichtbar und nicht still per `last wins` oder `first wins` aufgeloest.
- `personal_fundamentals_evidence_composed.csv` bleibt ein separates Evidence-Artefakt. Die Nutzung im bestehenden Evidence-Workflow erfolgt nur explizit, z. B. im Orchestrator mit `--use-composed-evidence`.
- `personal_fundamentals_snapshot_evidence_promoted.csv` bleibt bewusst ein separates promoted Artefakt; die Uebernahme in `personal_fundamentals_evidence.csv` bleibt weiterhin ein expliziter manueller Folgeschritt.

## Fundamentals Overlay / Applied Master

`src.fundamentals_overlay_engine` ergaenzt den Personal-Master um eine explizite lokale Analyst-Overlay-Schicht. Der manuelle Input `data/raw/personal_fundamentals_overlay.csv` wird validiert, zu `data/processed/personal_fundamentals_overlay_registry.csv` normalisiert und als `data/processed/personal_fundamentals_master_applied.csv` auf den Personal-Master projiziert. `overlay_review_due_date` wird als `NOT_SET`, `OK`, `DUE` oder `OVERDUE` sichtbar und kann zusaetzlich in `personal_fundamentals_overlay_review_backlog.csv` ausgegeben werden.

```powershell
python -m src.fundamentals_overlay_engine --fundamentals-master data/raw/personal_fundamentals_master.csv --overlay-input data/raw/personal_fundamentals_overlay.csv --registry-output data/processed/personal_fundamentals_overlay_registry.csv --applied-master-output data/processed/personal_fundamentals_master_applied.csv --summary-output data/processed/personal_fundamentals_overlay_summary.csv --review-backlog-output data/processed/personal_fundamentals_overlay_review_backlog.csv --report-output reports/YYYY-MM-DD/personal_fundamentals_overlay_report.md --template-output data/raw/personal_fundamentals_overlay_template.csv
```

Leitplanken:

- Holding-Zuordnung erfolgt nur ueber exakte Ticker-/ISIN-Identitaet gegen den Personal-Master.
- Die Applied-Master-Projektion veraendert keine Core-KPIs und schreibt nicht in `data/raw/personal_fundamentals_master.csv` zurueck.
- Es gibt keine neue Scoring-Logik, keine automatische Research-/PDF-/Web-/API-Extraktion und keine automatische Uebernahme in Scores.
- `personal_fundamentals_master_applied.csv` ist eine explizite Projektion fuer nachgelagerte Fundamentals-/Scoring-Pfade, wenn sie bewusst als `--fundamentals` uebergeben wird; sie ersetzt den Original-Master nicht still.
- Faellige oder ueberfaellige Overlay-Reviews werden markiert, aber Overlays werden dadurch nicht automatisch deaktiviert.

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

Historisches Snapshot-Archiv:

- `src.portfolio_history_engine` baut aus expliziten Positions-Snapshots ein persistentes `data/processed/portfolio_snapshot_archive.csv`.
- Daraus wird eine normalisierte `data/processed/portfolio_timeseries.csv` im Format von `src.performance_engine` erzeugt.
- Pro Datum wird nur ein Archivpunkt akzeptiert. Ein identischer Wiederholungslauf ist idempotent; abweichende Werte fuer ein bereits archiviertes Datum werden hart abgewiesen.
- Es werden keine Zwischenpunkte, externen Cashflows, TWR/IRR-Werte oder nicht belegte Historie rekonstruiert.

Explizite Historien-KPIs:

- `rolling_return_1m`, `rolling_return_3m`, `rolling_return_6m` und `rolling_return_12m` werden nur berechnet, wenn ein expliziter NAV-Startpunkt innerhalb von `+/- 7` Kalendertagen um den nominalen Fensterstart liegt.
- `max_drawdown` nutzt nur explizite NAV-Peak-/Trough-Punkte.
- `volatility` ist eine unannualisierte Sample-Standardabweichung expliziter aufeinanderfolgender Punkt-Returns.
- Ohne passend tiefe oder passend datierte Historie bleiben diese KPIs `INSUFFICIENT_HISTORY`.

Snapshot historisieren und anschliessend Performance ausfuehren:

```powershell
python -m src.portfolio_history_engine --positions data/processed/personal_positions_snapshot.csv --archive data/processed/portfolio_snapshot_archive.csv --archive-output data/processed/portfolio_snapshot_archive.csv --timeseries-output data/processed/portfolio_timeseries.csv --summary-output data/processed/portfolio_history_summary.csv --report-output reports/YYYY-MM-DD/portfolio_history_report.md
python -m src.performance_engine --positions data/processed/personal_positions_snapshot.csv --portfolio-timeseries data/processed/portfolio_timeseries.csv --benchmark data/raw/sample_benchmark_timeseries.csv --benchmark-config configs/benchmark.yaml --comparison-output data/processed/performance_comparison.csv --kpi-output data/processed/performance_kpis.csv --report-output reports/sample/performance_report.md
```

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

Persistentes Benchmark-Archiv:

- `src.benchmark_history_engine` normalisiert explizite lokale Benchmark-Zeitreihen mit der bestehenden Benchmark-Normalisierung aus `src.performance_engine`.
- Das Archiv `data/processed/benchmark_timeseries_archive.csv` kann mehrere Benchmark-Symbole halten.
- Die starke Archiv-Identitaet ist `benchmark_symbol` + `date`. Identische normalisierte Zeilen sind idempotent; dieselbe Identitaet mit abweichenden Werten wird hart abgewiesen.
- Symbolweite Metadaten wie `benchmark_name`, `currency` und `benchmark_return_basis_used` duerfen pro Symbol nicht still driften.
- `data/processed/benchmark_registry.csv` fasst pro Symbol `first_date`, `last_date`, `points_count`, Return-Basis, Source und Datenqualitaet zusammen.
- `data/processed/benchmark_timeseries_normalized.csv` bleibt fuer `src.performance_engine` eine explizit ausgewaehlte Einzelreihe im bestehenden `BENCHMARK_NORMALIZED_FIELDS`-Format. Bei mehreren Symbolen ist `--benchmark-symbol` Pflicht.
- Es gibt keine externe API, keine FX-Schicht, keine Interpolation und keine Auffuellung fehlender Benchmark-Punkte.

Multi-Benchmark-Vergleich aus Archiv und Registry:

- `src.multi_benchmark_performance_engine` vergleicht dieselbe explizite Portfolio-Zeitreihe gegen mehrere ausgewaehlte Benchmark-Symbole aus `benchmark_timeseries_archive.csv` und `benchmark_registry.csv`.
- Die Vergleichssemantik bleibt die Single-Benchmark-Methodik aus `src.performance_engine`: `relative_performance_pct` entspricht Portfolio-Return minus Benchmark-Return.
- Wenn Archiv oder Registry mehrere Symbole enthalten, ist eine explizite wiederholbare `--benchmark-symbol`-Auswahl erforderlich; es gibt keine stille Voll- oder Default-Auswahl.
- Stale-, Approx-Price-Only- und unzureichende Historie werden pro Benchmark-Reihe in `data_quality_flag` markiert.
- Es gibt keine externe API, keine FX-Schicht, keine Benchmark-Blends und keine Interpolation.

Neue Artefakte:

- `data/processed/benchmark_timeseries_archive.csv`
- `data/processed/benchmark_registry.csv`
- `data/processed/benchmark_timeseries_normalized.csv`
- `data/processed/multi_benchmark_comparison.csv`
- `data/processed/multi_benchmark_summary.csv`
- `data/processed/multi_benchmark_kpis.csv`
- optional `data/processed/benchmark_archive_summary.csv`
- `data/processed/portfolio_snapshot_archive.csv`
- `data/processed/portfolio_timeseries.csv`
- `data/processed/portfolio_history_summary.csv`
- `data/processed/performance_summary.csv`
- `data/processed/performance_comparison.csv`
- `data/processed/performance_kpis.csv`
- optional `reports/YYYY-MM-DD/benchmark_history_report.md`
- `reports/YYYY-MM-DD/portfolio_history_report.md`
- `reports/YYYY-MM-DD/performance_report.md`
- `reports/YYYY-MM-DD/multi_benchmark_report.md`

Benchmark-Archiv bauen und Performance mit der ausgewaehlten Reihe ausfuehren:

```powershell
python -m src.benchmark_history_engine --benchmark-input data/raw/sample_benchmark_timeseries.csv --benchmark-config configs/benchmark.yaml --archive data/processed/benchmark_timeseries_archive.csv --archive-output data/processed/benchmark_timeseries_archive.csv --normalized-output data/processed/benchmark_timeseries_normalized.csv --registry-output data/processed/benchmark_registry.csv --archive-summary-output data/processed/benchmark_archive_summary.csv --report-output reports/YYYY-MM-DD/benchmark_history_report.md --benchmark-symbol SAMPLE_WORLD_TR_EUR
python -m src.performance_engine --positions data/processed/personal_positions_snapshot.csv --portfolio-timeseries data/processed/portfolio_timeseries.csv --benchmark data/processed/benchmark_timeseries_normalized.csv --benchmark-config configs/benchmark.yaml --comparison-output data/processed/performance_comparison.csv --kpi-output data/processed/performance_kpis.csv --report-output reports/sample/performance_report.md
```

Multi-Benchmark-Vergleich aus Archiv und Registry:

```powershell
python -m src.multi_benchmark_performance_engine --positions data/processed/personal_positions_snapshot.csv --portfolio-timeseries data/processed/portfolio_timeseries.csv --benchmark-archive data/processed/benchmark_timeseries_archive.csv --benchmark-registry data/processed/benchmark_registry.csv --benchmark-config configs/benchmark.yaml --benchmark-symbol SAMPLE_WORLD_TR_EUR --benchmark-symbol SAMPLE_EUROPE_TR_EUR --comparison-output data/processed/multi_benchmark_comparison.csv --summary-output data/processed/multi_benchmark_summary.csv --kpi-output data/processed/multi_benchmark_kpis.csv --report-output reports/YYYY-MM-DD/multi_benchmark_report.md
```

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

- `data/processed/cost_tax_ledger_archive.csv`
- `data/processed/cost_tax_ledger_normalized.csv`
- `data/processed/cost_tax_summary.csv`
- `data/processed/cost_tax_kpis.csv`
- optional `data/processed/cost_tax_archive_summary.csv`
- `reports/YYYY-MM-DD/cost_tax_report.md`

Persistenter Archivpfad:

- `src.cost_tax_archive_engine` fuehrt manuelle Ledger-Zeilen und unterstuetzte Dokumentinputs erst nach Normalisierung in einem persistenten Archiv zusammen.
- Die starke Archiv-Identitaet ist `broker`, `reference_id`, `record_granularity`, `event_type`, `event_date`, `ticker`, `isin`, `document_period_start` und `document_period_end`.
- Identische normalisierte Zeilen mit derselben Identitaet sind idempotent. Dieselbe Identitaet mit abweichenden fachlichen Feldwerten wird hart abgewiesen; es gibt kein `last write wins`.
- Summary, KPI und Report werden anschliessend weiter ueber die bestehende Cost-/Tax-Logik aus dem finalen Archiv abgeleitet.
- Das Archiv rekonstruiert keine Lot-, FIFO-, Average-Cost- oder Steuerhistorie und nutzt keine Snapshot-Felder wie `avg_cost`, `cost_basis_eur` oder `unrealized_pnl_eur` als Ersatzledger.

Sample-CLI:

```powershell
python -m src.cost_tax_engine --ledger data/raw/sample_cost_tax_ledger.csv --summary-output data/processed/cost_tax_summary.csv --kpi-output data/processed/cost_tax_kpis.csv --report-output reports/sample/cost_tax_report.md
```

Persistenter Archivlauf:

```powershell
python -m src.cost_tax_archive_engine --ledger data/raw/personal_cost_tax_ledger.csv --document-input data/raw/private/traderepublic/Steuerbericht_2024.pdf --archive data/processed/cost_tax_ledger_archive.csv --archive-output data/processed/cost_tax_ledger_archive.csv --normalized-ledger-output data/processed/cost_tax_ledger_normalized.csv --summary-output data/processed/cost_tax_summary.csv --kpi-output data/processed/cost_tax_kpis.csv --report-output reports/YYYY-MM-DD/cost_tax_report.md --archive-summary-output data/processed/cost_tax_archive_summary.csv
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

## Persoenlicher Run-Orchestrator

`src.personal_run_engine` koordiniert ausgewaehlte persoenliche Stages ueber die bestehenden kanonischen Engines. Er fuehrt keine neue Scoring-, Matching-, Performance-, Benchmark-, Tax- oder Dashboard-Fachlogik ein. Jede Stage muss explizit mit `--stage` angefordert werden; es gibt keinen stillen Komplettlauf.

Neue Run-Artefakte:

- `data/processed/personal_run_manifest.json`: Run-Status, ausgewaehlte und tatsaechlich ausgefuehrte Stages, Inputs, Outputs, Stage-Ergebnisse, Warnings, Measurement Modes und Datenqualitaetsflags
- `data/processed/personal_run_artifacts.csv`: kompakter Artefaktindex je Stage
- `data/processed/personal_run_used_inputs.csv`: flacher, auditierbarer Input-Lineage-Index je Stage aus den echten `StageResult.used_inputs`
- `data/processed/personal_data_source_status.csv`: flacher Status-Export der read-only Personal-Run-Source-Registry
- `data/processed/personal_data_source_registry_resolved.csv`: sichtbare Aufloesung, welche Registry-Quellen als Default-Inputs dienen koennen
- `reports/YYYY-MM-DD/personal_run_report.md`: knapper operativer Run-Ueberblick

Die additive read-only Source-Registry fuer den persoenlichen Lauf liegt in `configs/personal_run_data_sources.yaml`. Sie schliesst nur lokale Dateiquellen kontrolliert an; Secrets, API-Keys und direkte Web-/API-Logik gehoeren nicht in diese Schicht.

Core-Orchestrator-Beispiel:

```powershell
python -m src.personal_run_engine --stage import --stage fundamentals_seed --stage scoring --stage coverage --stage watchlist --stage monthly --stage portfolio_review --positions-raw-input data/raw/personal_depot.csv --import-mode real --source-name personal_depot --fundamentals-master data/raw/personal_fundamentals_master.csv --watchlist-input data/raw/sample_watchlist.csv --manifest-output data/processed/personal_run_manifest.json --artifacts-output data/processed/personal_run_artifacts.csv --used-inputs-output data/processed/personal_run_used_inputs.csv --report-output reports/YYYY-MM-DD/personal_run_report.md
```

Hinweise:

- `data_sources_validate` validiert nur die Personal-Run-Source-Registry und schreibt `personal_data_source_status.csv` sowie `personal_data_source_registry_resolved.csv`; es fuehrt keine neue Fachlogik ein.
- Input-Prioritaet im Orchestrator bleibt explizit: gesetzter CLI-Pfad, dann `configs/personal_run_data_sources.yaml`, dann bestehender Repo-Default. Es gibt keinen stillen Fantasie-Fallback.
- Die Personal-Source-Registry kann fuer diesen Pfad optional `fundamentals_snapshot_evidence_promoted_input` auf ein separates promoted Snapshot-Evidence-Artefakt zeigen; sie fuehrt keine neue Evidence- oder Source-Mode-Logik ein.
- `scoring` bleibt eine eigenstaendige Stage und wird nicht in `fundamentals_seed` oder `coverage` versteckt.
- `fundamentals_seed` erzeugt nur Identity-Seed-Zeilen und erfindet keine KPI-Werte. Ein vorhandener Personal-Master wird nur mit `--overwrite-fundamentals-master` ersetzt.
- `coverage` erzeugt neben Coverage, Enriched und Report auch `personal_research_priority.csv` als operative Nachpflege-Liste fuer Profile/KPI-Luecken.
- `fundamentals_profile` erzeugt nur Profile-Registry, Review-Backlog und `personal_fundamentals_master_profiled.csv`; diese Stage schreibt nicht in den Raw-Master zurueck und schaltet Downstream-Stages nicht automatisch um.
- `fundamentals_snapshot_ingest` liest nur einen lokalen externen Fundamentals-Snapshot, schreibt `personal_fundamentals_snapshot_normalized.csv`, `personal_fundamentals_snapshot_unmatched.csv`, `personal_fundamentals_snapshot_evidence_staging.csv` und `personal_fundamentals_snapshot_summary.csv` und aendert weder Raw-Master noch manuelle Evidence-CSV.
- `fundamentals_snapshot_review` liest nur den vorhandenen Snapshot-Evidence-Staging-Output plus einen expliziten manuellen Review-Input, schreibt `personal_fundamentals_snapshot_review_registry.csv`, `personal_fundamentals_snapshot_evidence_promoted.csv`, `personal_fundamentals_snapshot_review_backlog.csv` und `personal_fundamentals_snapshot_review_summary.csv` und merged nichts automatisch in `personal_fundamentals_evidence.csv` oder den Master.
- `fundamentals_evidence_compose` fuehrt nur `data/raw/personal_fundamentals_evidence.csv` und `personal_fundamentals_snapshot_evidence_promoted.csv` explizit in `personal_fundamentals_evidence_composed.csv` zusammen, schreibt Konflikte/Summary separat und ueberschreibt niemals `personal_fundamentals_evidence.csv`.
- `--use-profiled-master` schaltet nur explizit geeignete fundamentals-abhaengige Stages wie `fundamentals_overlay`, `scoring`, `coverage`, `watchlist`, `monthly` und `portfolio_review` auf `personal_fundamentals_master_profiled.csv`. Ohne den Schalter bleibt der Base-Master aktiv; wenn der profiled Master fehlt, scheitert der Run fail-fast.
- `fundamentals_evidence` erzeugt nur Evidence-Registry, Research-Backlog, Summary und Evidence-Report; diese Stage schreibt nicht in den Personal-Master zurueck.
- `fundamentals_evidence` erzeugt zusaetzlich `personal_fundamentals_proposed_updates.csv` als manuellen Vorschlagsoutput aus validierter Evidence mit `reported_value`.
- `--use-composed-evidence` schaltet `fundamentals_evidence` explizit auf `personal_fundamentals_evidence_composed.csv`. Ohne den Schalter bleibt der bestehende Raw-/CLI-/Registry-Evidence-Input aktiv; ein abweichender expliziter `--fundamentals-evidence-input` ist dabei fuer `fundamentals_evidence` bewusst mehrdeutig und wird ausserhalb eines gleichzeitig ausgefuehrten `fundamentals_evidence_compose`-Schritts fail-fast abgewiesen.
- `fundamentals_overlay` erzeugt nur Overlay-Registry, Applied-Master-Projektion, Review-Backlog, Summary und Overlay-Report; diese Stage ersetzt den Original-Master nicht still.
- `--use-applied-master` schaltet nur explizit fundamentals-abhaengige Downstream-Stages wie `scoring`, `coverage`, `watchlist`, `monthly` und `portfolio_review` auf `personal_fundamentals_master_applied.csv`. Ohne den Schalter bleibt der Base-Master aktiv; wenn der Applied Master fehlt, scheitert der Run fail-fast.
- `--use-profiled-master` und `--use-applied-master` sind in dieser Iteration gegenseitig ausschliessend; es gibt keine neue Kaskade wie `PROFILED_APPLIED`.
- `personal_run_used_inputs.csv` enthaelt nur die tatsaechlich verwendeten Stage-Inputs; fuer fundamentals-abhaengige Stages macht das Feld `notes` `fundamentals_source_mode=BASE`, `fundamentals_source_mode=PROFILED` oder `fundamentals_source_mode=APPLIED` sichtbar.
- Der Used-Inputs-Index bleibt bewusst eine flache Projektion aus `StageResult.used_inputs`; wenn eine Stage lokale Config-Dateien real liest, erscheinen diese Pfade dort ebenfalls als Stage-Inputs.
- Wenn ein Input ueber `configs/personal_run_data_sources.yaml` als Default aufgeloest wurde, machen `personal_data_source_registry_resolved.csv` und die Stage-Notes dies sichtbar; das ersetzt keine tiefere engine-interne Lineage.
- Die persoenlichen Orchestrator-Defaults fuer Watchlist-, Monthly- und Portfolio-Review-Reports schreiben nach `reports/YYYY-MM-DD/personal_watchlist_report.md`, `reports/YYYY-MM-DD/personal_monthly_decision_report.md` und `reports/YYYY-MM-DD/personal_portfolio_review.md`, nicht nach `reports/sample/...`.
- Multi-Benchmark-Stages behalten die expliziten Symbolauswahl-Regeln aus `src.multi_benchmark_performance_engine`; bei mehreren Symbolen gibt es keine stille Auswahl.
- `history` und `performance` brauchen einen datierten Snapshot. Bei `--import-mode sample` sollte deshalb `--portfolio-date` explizit gesetzt werden.
- Die Einzel-CLIs unten bleiben weiterhin gueltig und sind die fachlichen Modulvertraege.

## Persoenlicher Lauf

Der persoenliche Lauf kann entweder ueber einen manuellen CSV-Depotexport oder ueber offizielle textbasierte Trade-Republic-Dokumente erfolgen. Der PDF-Pfad nutzt lokal nur `data/raw/private/traderepublic/Depotauszug.pdf` fuer Holdings und `data/raw/private/traderepublic/Kontoauszug.pdf` fuer den Cash-Endsaldo.

Empfohlener persoenlicher CSV-Lauf:

```powershell
python -m src.import_broker --input data/raw/personal_depot.csv --output data/processed/personal_positions_snapshot.csv --mode real --source-name personal_depot
python -m src.fundamentals_master --positions data/processed/personal_positions_snapshot.csv --init-master-output data/raw/personal_fundamentals_master.csv
python -m src.scoring_engine --positions data/processed/personal_positions_snapshot.csv --fundamentals data/raw/personal_fundamentals_master.csv --fundamentals-format personal --output data/processed/personal_company_scores.csv --audit-output data/processed/personal_score_audit.csv
python -m src.fundamentals_master --positions data/processed/personal_positions_snapshot.csv --fundamentals data/raw/personal_fundamentals_master.csv --scores data/processed/personal_company_scores.csv --coverage-output data/processed/personal_fundamentals_coverage.csv --enriched-output data/processed/personal_fundamentals_enriched.csv --research-priority-output data/processed/personal_research_priority.csv --report-output reports/YYYY-MM-DD/personal_fundamentals_coverage_report.md
python -m src.watchlist_engine --input data/raw/sample_watchlist.csv --scores data/processed/personal_company_scores.csv --output data/processed/personal_watchlist_ranked.csv --report-output reports/YYYY-MM-DD/personal_watchlist_report.md
python -m src.monthly_ranking_engine --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --watchlist data/processed/personal_watchlist_ranked.csv --coverage data/processed/personal_fundamentals_coverage.csv --output data/processed/personal_monthly_buy_ranking.csv --rebalance-output data/processed/personal_rebalance_proposals.csv
python -m src.build_monthly_decision_report --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --ranking data/processed/personal_monthly_buy_ranking.csv --coverage data/processed/personal_fundamentals_coverage.csv --output reports/YYYY-MM-DD/personal_monthly_decision_report.md
python -m src.build_portfolio_snapshot --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --coverage data/processed/personal_fundamentals_coverage.csv --holdings-output data/processed/personal_portfolio_holdings_action_table.csv --output reports/YYYY-MM-DD/personal_portfolio_review.md
```

Empfohlener persoenlicher Trade-Republic-PDF-Lauf:

```powershell
python -m src.import_broker --input data/raw/private/traderepublic/Depotauszug.pdf --cash-input data/raw/private/traderepublic/Kontoauszug.pdf --output data/processed/personal_positions_snapshot.csv --mode tr_pdf --source-name trade_republic_official_docs
python -m src.fundamentals_master --positions data/processed/personal_positions_snapshot.csv --init-master-output data/raw/personal_fundamentals_master.csv
python -m src.scoring_engine --positions data/processed/personal_positions_snapshot.csv --fundamentals data/raw/personal_fundamentals_master.csv --fundamentals-format personal --output data/processed/personal_company_scores.csv --audit-output data/processed/personal_score_audit.csv
python -m src.fundamentals_master --positions data/processed/personal_positions_snapshot.csv --fundamentals data/raw/personal_fundamentals_master.csv --scores data/processed/personal_company_scores.csv --coverage-output data/processed/personal_fundamentals_coverage.csv --enriched-output data/processed/personal_fundamentals_enriched.csv --research-priority-output data/processed/personal_research_priority.csv --report-output reports/YYYY-MM-DD/personal_fundamentals_coverage_report.md
python -m src.watchlist_engine --input data/raw/sample_watchlist.csv --scores data/processed/personal_company_scores.csv --output data/processed/personal_watchlist_ranked.csv --report-output reports/YYYY-MM-DD/personal_watchlist_report.md
python -m src.monthly_ranking_engine --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --watchlist data/processed/personal_watchlist_ranked.csv --coverage data/processed/personal_fundamentals_coverage.csv --output data/processed/personal_monthly_buy_ranking.csv --rebalance-output data/processed/personal_rebalance_proposals.csv
python -m src.build_monthly_decision_report --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --ranking data/processed/personal_monthly_buy_ranking.csv --coverage data/processed/personal_fundamentals_coverage.csv --output reports/YYYY-MM-DD/personal_monthly_decision_report.md
python -m src.build_portfolio_snapshot --positions data/processed/personal_positions_snapshot.csv --scores data/processed/personal_company_scores.csv --coverage data/processed/personal_fundamentals_coverage.csv --holdings-output data/processed/personal_portfolio_holdings_action_table.csv --output reports/YYYY-MM-DD/personal_portfolio_review.md
```

Interpretation der persoenlichen Outputs:

- `personal_positions_snapshot.csv`: normalisierte Bestandsdaten aus dem privaten Depotexport
- `personal_fundamentals_master.csv`: lokale Source of Truth fuer persoenliche Fundamentals; initiale Seed-Zeilen aus dem Snapshot enthalten nur Identitaet und muessen manuell mit belegten KPIs ergaenzt werden
- `personal_company_scores.csv`: Score- und Bewertungsdaten fuer die persoenlichen Holdings, bevorzugt aus dem Personal-Master statt aus Sample-Fundamentals
- `personal_score_audit.csv`: nachvollziehbare KPI-/Teilscore-/Buy-Score-Auditspur mit `fundamentals_input_format`
- `personal_fundamentals_coverage.csv`: Match- und Coverage-Status je Holding inklusive `missing_required_kpis`, `not_applicable_kpis` und `needs_research_flag`
- `personal_fundamentals_enriched.csv`: gematchte Holdings mit Master-Roh-KPIs, bestehenden Teil-Scores und Source-Metadaten
- `personal_fundamentals_coverage_report.md`: Markdown-Report mit COVERED/PARTIAL/REVIEW/NO_MATCH und Research-Luecken
- `personal_research_priority.csv`: operative Nachpflege-Liste fuer unbegruendete `OTHER`-Profile und offene Pflicht-KPI-Luecken, sortiert nach Portfoliorelevanz
- `personal_fundamentals_evidence_registry.csv`: normalisierte lokale Evidence-Zeilen je Holding/KPI/Quelle
- `personal_fundamentals_research_backlog.csv`: operative Evidence-Luecken je Holding auf Basis der kanonischen Required-KPI-Methodik
- `personal_fundamentals_proposed_updates.csv`: manueller Vorschlagsoutput aus validierter Evidence mit `reported_value`; keine automatische Master-Rueckschreibung
- `personal_fundamentals_snapshot_normalized.csv`: read-only ingestierte lokale Fundamentals-Snapshot-Werte je exakt gematchter Personal-Identitaet
- `personal_fundamentals_snapshot_unmatched.csv`: lokale Fundamentals-Snapshot-Zeilen ohne exakten Personal-Master-Match
- `personal_fundamentals_snapshot_evidence_staging.csv`: aus dem Snapshot abgeleitete manuelle Evidence-Staging-Zeilen; keine automatische Uebernahme in `personal_fundamentals_evidence.csv`
- `personal_fundamentals_snapshot_summary.csv`: Ingest-/Match-/Staging-Summary fuer den lokalen Snapshot-Import
- `personal_fundamentals_snapshot_review_registry.csv`: normalisierte manuelle Review-Entscheidungen je Snapshot-Staging-Identitaet
- `personal_fundamentals_snapshot_evidence_promoted.csv`: separat freigegebene Snapshot-Evidence im bestehenden Evidence-Input-Vertrag; weiterhin kein automatischer Merge in `personal_fundamentals_evidence.csv`
- `personal_fundamentals_snapshot_review_backlog.csv`: offene Snapshot-Review-Faelle ohne Entscheidung oder mit `PENDING`
- `personal_fundamentals_snapshot_review_summary.csv`: Review-/Promote-Summary fuer den Snapshot-Freigabepfad
- `personal_fundamentals_evidence_composed.csv`: explizit zusammengesetztes Evidence-Artefakt aus Raw-Manual-Evidence und promoted Snapshot-Evidence; weiterhin kein automatisches Ueberschreiben von `personal_fundamentals_evidence.csv`
- `personal_fundamentals_evidence_compose_conflicts.csv`: explizite Konfliktzeilen aus dem Compose-Schritt; keine stille Priorisierung
- `personal_fundamentals_evidence_compose_summary.csv`: Compose-Summary fuer Manual-/Promoted-Evidence, Dedupe und Konfliktzaehlung
- `personal_fundamentals_overlay_registry.csv`: normalisierte lokale Analyst-Overlay-Zeilen je Holding/Stichtag/Autor
- `personal_fundamentals_master_applied.csv`: explizite Projektion aus Original-Master plus validierten Overlays; kein Ersatz fuer die Core-KPI-Source-of-Truth
- `personal_fundamentals_overlay_review_backlog.csv`: faellige oder ueberfaellige Overlay-Reviews; keine automatische Overlay-Deaktivierung
- `personal_run_used_inputs.csv`: flacher Input-Lineage-Index fuer den persoenlichen Orchestrator; keine Output-Artefakte und keine hypothetischen Inputs
- `personal_portfolio_holdings_action_table.csv`: operative Holdings-Aktionen `ADD`, `HOLD`, `WATCH`, `REDUCE`, `EXIT_REVIEW`; bei uebergebener Coverage werden offene Fundamentals-Luecken konservativ als Guardrail sichtbar
- `personal_monthly_buy_ranking.csv`: Kauf-Ranking fuer den konfigurierten Monatszufluss; bei uebergebener Coverage werden bestehende Holdings mit offenen Fundamentals-Luecken nicht fuer frisches Kapital empfohlen
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
