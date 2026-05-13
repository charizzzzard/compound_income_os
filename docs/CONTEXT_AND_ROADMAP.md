# Context And Roadmap

## Status-Legende

- `TRACKED_HEAD`: aus `git ls-files` und aktuellem HEAD abgeleitete Repo-Realitaet.
- `LOCAL_WORKTREE_ONLY`: beobachtete, derzeit dirty oder untracked lokale Dateien. Diese sind nicht automatisch kanonische Repo-Architektur.
- `ROADMAP`: beabsichtigtes oder spaeteres Zielbild, nicht als operatives Ist zu lesen.

## TRACKED_HEAD Ist-Zustand

Das getrackte Repo enthaelt `AGENTS.md`, `README.md`, `configs/`, `data/`, `reports/`, `research/`, `src/`, `tests/`, `website/`, `_archive/sec/`, `_archive/personal_meta/` und diese Governance-Dokumentation unter `docs/`.

Getrackte Kernmodule sind:

- `src.import_broker`, `src.normalize_positions` und `src.traderepublic_documents` fuer read-only Import und Normalisierung lokaler Depot-/Dokumentdaten
- `src.savings_plan_registry` fuer ein manuell gepflegtes read-only Sparplan-Register ohne Broker-Schreiblogik
- `src.savings_plan_routing` fuer read-only Sparplan-Routing-Empfehlungen pro Buy-Kandidat ohne Order-Ausfuehrung, Broker-API oder Decision-Capture-Schemaaenderung
- `src.scoring_engine`, `src.fundamentals_engine`, `src.fundamentals_master`, `src.fundamentals_evidence_engine`, `src.fundamentals_overlay_engine`, `src.valuation_engine` und `src.company_master` fuer Score-, Fundamentals-, Personal-Master-, Evidence-/Research-Backlog-, Overlay-/Applied-Master- und Bewertungslogik
- `src.portfolio_rules`, `src.portfolio_review`, `src.watchlist_engine` und `src.monthly_ranking_engine` fuer Portfolio-Regeln, Holdings-Aktionen, Watchlist und Monatsranking
- `src.build_portfolio_snapshot` und `src.build_monthly_decision_report` fuer Markdown-Reports aus verarbeiteten Artefakten
- `src.performance_engine`, `src.benchmark_history_engine`, `src.multi_benchmark_performance_engine`, `src.portfolio_history_engine`, `src.cost_tax_engine`, `src.cost_tax_archive_engine`, `src.dashboard_engine` und `src.dashboard_server` fuer Performance-/Benchmark-, Benchmark-Archiv-, Multi-Benchmark-, Portfolio-Historien-, Cost-/Tax-Archiv-, Cost-/Tax-, Dashboard- und lokalen Dashboard-Viewer-Artefakte
- `src.personal_run_engine` fuer explizite persoenliche Stage-Orchestrierung, Run-Manifest, Artefaktindex und Run-Report
- `src.common` fuer gemeinsame Pfad-, CSV-, Config-, Parsing- und Score-Helfer
- `src.platform` fuer minimale stdlib-only Foundation-Helfer: Schema-Registry, Validierung und atomare Artefakt-IO

Getrackte Konfigurationen liegen unter `configs/` und decken Portfolio-Regeln, Scoring-Gewichte, Fundamentals-Schema, Fundamentals-Score-Regeln, Fundamentals-Metric-Definitionen, Watchlist, Sparplan-Routing-Schwellen, Datenquellen, Benchmark, Cost/Tax und Dashboard-KPIs ab.

Die getrackten Tests liegen unter `tests/test_*.py` und nutzen `unittest`. Sie pruefen unter anderem README-Portabilitaet, Import/Normalisierung, Scoring, Raw-/Legacy-/Personal-Fundamentals, Watchlist, Monatsranking, Reports, Performance, Cost/Tax, Dashboard und Trade-Republic-Dokumentparser.

Website-Code und Website-Tests liegen seit Patch 1 separat unter `website/src/` und `website/tests/`; sie sind nicht Teil des aktiven Core-Test-Discoverys unter `tests/`.

## Dirty-/Untracked-Regel

`LOCAL_WORKTREE_ONLY` ist eine Arbeitskategorie fuer kuenftige Repo-Pruefungen, nicht der aktuelle Status des Personal-Masters. Dateien in diesem Zustand duerfen erst nach fachlicher Annahme und Tracking als kanonische Architektur beschrieben werden. Der Personal-Master ist nach seiner Uebernahme in `TRACKED_HEAD` oben als kanonischer Bestandteil dokumentiert.

## Reale Pipeline-Phasen

1. Import: `src.import_broker` normalisiert lokale CSV- oder textbasierte Dokumentinputs in Positions-Snapshots.
2. Sparplan: `src.savings_plan_registry` validiert ein manuell gepflegtes Sparplan-Register (`data/raw/savings_plan_registry.csv`) und erzeugt `data/processed/savings_plan_registry_summary.csv` plus Markdown-Report. Der Schritt ist ein read-only Spiegel ohne Routing-Logik, ohne Decision-Output und ohne Broker-Write.
3. Fundamentals Seed: `src.fundamentals_master` erzeugt aus Positions-Snapshots einen Identity-only Personal-Fundamentals-Master, ohne KPI-Werte zu erfinden.
4. Scoring: `src.scoring_engine` verbindet Positionen mit Fundamentals und erzeugt Company Scores, optional Score-Audit und angereicherte Fundamentals.
5. Personal-Master/Evidence/Overlay: `src.fundamentals_master` validiert lokale Personal-Fundamentals, matched Holdings konservativ und erzeugt Coverage-/Research-Gap-Artefakte; `src.fundamentals_evidence_engine` validiert explizite lokale KPI-Evidence und erzeugt Registry-/Research-Backlog-Artefakte ohne Rueckschreibung in den Master; `src.fundamentals_profile_engine` kann denselben Profil-Review-Vertrag explizit auf dem Evidence+Identity-Master anwenden und daraus einen separaten profiled Master projizieren; `src.fundamentals_gap_diagnostics` erklaert read-only, ob verbleibende Luecken Profil-, SEC-, Markt- oder Scope-Ursachen haben; `src.fundamentals_overlay_engine` validiert explizite Analyst-Overlays und erzeugt eine Applied-Master-Projektion ohne Mutation des Original-Masters.
6. Watchlist: `src.watchlist_engine` kombiniert Watchlist-Kandidaten mit Scores.
7. Portfolio Review: `src.portfolio_review` erzeugt die bestehende per-Position-Holdings-Aktionstabelle ohne Portfolio-Health-Aggregation.
8. Phase 1.3 Portfolio Health: `src.cash_refill_review` meldet `CASH_REFILL_REQUIRED` bei Unterschreitung von `min_cash_reserve_eur` oder Cash-Bucket-Floor. `src.rebalance_review` erzeugt pro Bucket eine read-only Empfehlung `HOLD` / `DEPLOY_NEW_CASH` / `TRIM_FOR_REBALANCE_REVIEW` mit Cash-first-Logik. Keine Sells, keine Steuer-Quantifizierung, keine Blockade von Monthly-Ranking-Buy-Kandidaten.
9. Monatsranking: `src.monthly_ranking_engine` erzeugt Monatsranking und Rebalance-Vorschlaege aus Positionen, Scores, Watchlist und Portfolio-Regeln.
10. Routing: `src.savings_plan_routing` entscheidet pro Buy-Kandidat zwischen `SAVINGS_PLAN_EXISTING`, `SAVINGS_PLAN_NEW`, `SINGLE_ORDER` oder `NO_RECOMMENDATION` anhand der Vision-v1.2-§4.2-Logik. Read-only Empfehlung; keine Order-Ausfuehrung, keine Broker-API, keine Decision-Capture-Schemaaenderung.
11. Reports: `src.build_portfolio_snapshot` und `src.build_monthly_decision_report` erzeugen Markdown aus verarbeiteten Artefakten; der Monatsbericht rendert Portfolio Health vor den Buy-Kandidaten und kann `execution_mode`/`execution_mode_reason` fuer Buy-Kandidaten anzeigen, ohne Broker-Anweisung oder Decision-Capture-Felder zu erzeugen.
12. Performance und Benchmark: `src.portfolio_history_engine` baut aus expliziten Positions-Snapshots Archiv-/Timeseries-Artefakte; `src.benchmark_history_engine` baut aus expliziten lokalen Benchmark-Zeitreihen ein persistentes Archiv, eine Registry und eine einzelne Performance-kompatible Normalized-Reihe; `src.performance_engine` erzeugt Benchmark-/Performance-Artefakte mit Snapshot-, Perioden- und expliziten Historien-KPIs; `src.multi_benchmark_performance_engine` vergleicht mehrere explizit ausgewaehlte Archiv-/Registry-Benchmark-Symbole gegen dieselbe Portfolio-Zeitreihe.
13. Cost/Tax: `src.cost_tax_archive_engine` kann belegte manuelle oder Dokumentdaten in ein persistentes normalisiertes Archiv mergen; `src.cost_tax_engine` erzeugt daraus bzw. aus direkten Inputs Ledger-, Summary-, KPI- und Report-Artefakte.
14. Dashboard: `src.dashboard_engine` konsolidiert verarbeitete Artefakte in KPI-, Section-, Summary-, Universe- und Markdown-Ausgaben; die Universe-Sektion schreibt `data/processed/dashboard_universe_section.csv` mit stabiler Header-Reihenfolge als read-only Konsolidierung aus Holdings, Watchlist, Scores und Sparplan-Aktivstatus, ohne neue Scores zu berechnen oder Entscheidungen abzuleiten. `src.dashboard_server` stellt diese Dashboard-CSVs plus bestehende processed Decision-/Coverage-/Ledger-/Timeseries-Artefakte read-only als lokalen localhost-Viewer bereit, ohne neue Finanzlogik, ohne Imputation und mit einem expliziten History-Gate unter 12 Punkten.
15. Persoenlicher Orchestrator: `src.personal_run_engine` fuehrt nur explizit angeforderte Stages in kanonischer Reihenfolge aus und protokolliert Run-Status, Inputs, Outputs, Warnings und Stage-Ergebnisse in Manifest-/Artefakt-Outputs.
16. KPI Tier Guardrails: Fundamentals-, Scoring- und Monthly-Ranking-Pfade unterscheiden Core-Quality-, Valuation-, Dividend-FCF- und Advanced-Datenqualitaet. Fehlende Tier-Daten bleiben sichtbar und werden konservativ in Score-/Monthly-Guardrails verarbeitet.
17. SEC-Archiv: 26 ehemalige SEC-Module und 26 zugehoerige Tests liegen als read-only Referenz unter `_archive/sec/`. Sie sind nicht Teil der aktiven `src/`-Oberflaeche und werden durch `python -m unittest discover -s tests -p "test_*.py"` nicht mehr entdeckt.
16. Personal-Meta-Archiv: `src.personal_profile_review_materialize` und der zugehoerige Test liegen seit Patch 2.2b als read-only Referenz unter `_archive/personal_meta/`. Sie sind nicht Teil der aktiven `src/`-Oberflaeche und werden durch `python -m unittest discover -s tests -p "test_*.py"` nicht mehr entdeckt.
17. Handoff und Docs Drift: `src.handoff_zip_export` erzeugt standardisierte `outputs/handoffs/archive/`, `outputs/handoffs/latest/`- und `outputs/handoffs/upload_ready/`-Pakete fuer externe Review ohne private Daten. Docs-Drift wird ueber `docs/DOCUMENTATION_MAINTENANCE.md`, `docs/CODEX_TASKS/DOCS_DRIFT_CHECKLIST.md` und den lokalen Drift-Report sichtbar gemacht.
18. Architektur-Baseline: `docs/architecture/` fixiert das sechs-Kernel-Modell fuer Compound Income OS. `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md` definiert den Decision-Capture-Vertrag. `src.personal_decision_state_capture` implementiert den minimalen standalone Producer fuer append-only Entscheidungen und No-Actions; er erzeugt nur processed/report Artefakte und fuehrt keine Order-, Outcome-, Benchmark-Return-, Simulation- oder Backtesting-Logik aus. `docs/policies/LLM_CODEX_OPERATING_POLICY.md` haelt fest, dass LLMs/Codex assistieren und nicht entscheiden.

## ROADMAP / Spaeter

- Decision-Capture-Producer nach realer Nutzung auswerten, bevor Outcome Attribution, Simulation oder Backtesting starten.
- Evidence Capture fuer Fundamentals weiter schaerfen, ohne fehlende KPI-Werte zu erfinden oder Sample-Daten still fuer persoenliche Holdings zu nutzen.
- Archivierte SEC-Artefakte nur in einem separaten Re-Use-Patch reaktivieren; bis dahin keine aktive SEC-Fetch-/Refresh-Fachlogik im Core-Pfad voraussetzen.
- Dashboard-Runbooks nur erweitern, wenn sie aus bestehenden verarbeiteten Artefakten gespeist werden und keine neue Fachlogik einfuehren.
- Performance- und Cost-/Tax-Abdeckung nur dort vertiefen, wo passende Zeitreihen- oder Event-Evidenz vorhanden ist.
- SEC-Alias-Map oder Period-Selection nur nach separatem Re-Use-Design aus dem Archiv integrieren.
- Website-Mockups und Claude-Designmaterial unter `website/compound-income-os-landing/mockup/` als Referenzmaterial erhalten; Produktion bleibt unter `website/compound-income-os-landing/src/`.

## Definition Of Done fuer Patch-Arbeit

- Repo-Reality vor Aenderungen dokumentiert: Branch, HEAD, Worktree-Status und relevante Dateioberflaechen.
- Betroffene Modulgrenzen aus Code, Configs, README und Tests abgeleitet.
- Keine privaten Rohdaten, keine generierten Processed-Artefakte und keine Reports committed.
- Fehlende Daten bleiben sichtbar und werden nicht geraten.
- README-Pfade und CLI-Beispiele bleiben repo-portabel.
- Gezielte Tests und ein praktikabler `unittest`-Basislauf wurden ausgefuehrt oder ein Blocker wurde explizit dokumentiert.
- Nach dem Patch wurde die QA-Aufgabe in `docs/CODEX_TASKS/POST_ITERATION_QA.md` als Review-Schritt angewendet.
