# Context And Roadmap

## Status-Legende

- `TRACKED_HEAD`: aus `git ls-files` und aktuellem HEAD abgeleitete Repo-Realitaet.
- `LOCAL_WORKTREE_ONLY`: beobachtete, derzeit dirty oder untracked lokale Dateien. Diese sind nicht automatisch kanonische Repo-Architektur.
- `ROADMAP`: beabsichtigtes oder spaeteres Zielbild, nicht als operatives Ist zu lesen.

## TRACKED_HEAD Ist-Zustand

Das getrackte Repo enthaelt `AGENTS.md`, `README.md`, `configs/`, `data/`, `reports/`, `research/`, `src/`, `tests/` und diese Governance-Dokumentation unter `docs/`.

Getrackte Kernmodule sind:

- `src.import_broker`, `src.normalize_positions` und `src.traderepublic_documents` fuer read-only Import und Normalisierung lokaler Depot-/Dokumentdaten
- `src.scoring_engine`, `src.fundamentals_engine`, `src.fundamentals_master`, `src.personal_sec_scope_prepare`, `src.personal_sec_identity_export`, `src.external_sec_identity_resolve`, `src.external_sec_companyfacts_fetch`, `src.personal_sec_refresh_pipeline`, `src.fundamentals_evidence_engine`, `src.fundamentals_overlay_engine`, `src.valuation_engine` und `src.company_master` fuer Score-, Fundamentals-, lokalen SEC-Scope-Review-/Export, explizites SEC-Identity-Staging, SEC-Snapshot-Fetch, SEC-Refresh-Orchestrierung, Personal-Master-, Evidence-/Research-Backlog-, Overlay-/Applied-Master- und Bewertungslogik
- `src.portfolio_rules`, `src.portfolio_review`, `src.watchlist_engine` und `src.monthly_ranking_engine` fuer Portfolio-Regeln, Holdings-Aktionen, Watchlist und Monatsranking
- `src.build_portfolio_snapshot` und `src.build_monthly_decision_report` fuer Markdown-Reports aus verarbeiteten Artefakten
- `src.performance_engine`, `src.benchmark_history_engine`, `src.multi_benchmark_performance_engine`, `src.portfolio_history_engine`, `src.cost_tax_engine`, `src.cost_tax_archive_engine`, `src.dashboard_engine` und `src.dashboard_server` fuer Performance-/Benchmark-, Benchmark-Archiv-, Multi-Benchmark-, Portfolio-Historien-, Cost-/Tax-Archiv-, Cost-/Tax-, Dashboard- und lokalen Dashboard-Viewer-Artefakte
- `src.personal_run_engine` fuer explizite persoenliche Stage-Orchestrierung, Run-Manifest, Artefaktindex und Run-Report
- `src.common` fuer gemeinsame Pfad-, CSV-, Config-, Parsing- und Score-Helfer

Getrackte Konfigurationen liegen unter `configs/` und decken Portfolio-Regeln, Scoring-Gewichte, Fundamentals-Schema, Fundamentals-Score-Regeln, Fundamentals-Metric-Definitionen, Watchlist, Datenquellen, Benchmark, Cost/Tax und Dashboard-KPIs ab.

Die getrackten Tests liegen unter `tests/test_*.py` und nutzen `unittest`. Sie pruefen unter anderem README-Portabilitaet, Import/Normalisierung, Scoring, Raw-/Legacy-/Personal-Fundamentals, Watchlist, Monatsranking, Reports, Performance, Cost/Tax, Dashboard und Trade-Republic-Dokumentparser.

## Dirty-/Untracked-Regel

`LOCAL_WORKTREE_ONLY` ist eine Arbeitskategorie fuer kuenftige Repo-Pruefungen, nicht der aktuelle Status des Personal-Masters. Dateien in diesem Zustand duerfen erst nach fachlicher Annahme und Tracking als kanonische Architektur beschrieben werden. Der Personal-Master ist nach seiner Uebernahme in `TRACKED_HEAD` oben als kanonischer Bestandteil dokumentiert.

## Reale Pipeline-Phasen

1. Import: `src.import_broker` normalisiert lokale CSV- oder textbasierte Dokumentinputs in Positions-Snapshots.
2. Scoring: `src.scoring_engine` verbindet Positionen mit Fundamentals und erzeugt Company Scores, optional Score-Audit und angereicherte Fundamentals.
3. Personal-Master/Evidence/Overlay: `src.fundamentals_master` validiert lokale Personal-Fundamentals, matched Holdings konservativ und erzeugt Coverage-/Research-Gap-Artefakte; `src.personal_sec_scope_prepare` auditiert dirty Master-Identitaeten lokal fuer den US-`STOCK`-SEC-Scope und erzeugt eine manuelle Review-Datei; `src.personal_sec_identity_export` exportiert nur explizit approved Review-Zeilen in den bestehenden privaten SEC-Identity-Map-Vertrag; `src.external_sec_identity_resolve` staged offizielle SEC-Identity-Candidates ohne private Map-Schreibzugriff; `src.external_sec_companyfacts_fetch` kann explizit und read-only SEC CompanyFacts in ein lokales Snapshot-Artefakt fuer den bestehenden Snapshot-Pfad schreiben; `src.personal_sec_refresh_pipeline` orchestriert diesen Pfad mit separatem resolved Review-Artefakt und optionalem evidence-applied Downstream-Run; `src.fundamentals_evidence_engine` validiert explizite lokale KPI-Evidence und erzeugt Registry-/Research-Backlog-Artefakte ohne Rueckschreibung in den Master; `src.fundamentals_profile_engine` kann denselben Profil-Review-Vertrag explizit auf dem Evidence+Identity-Master anwenden und daraus einen separaten profiled Master projizieren; `src.fundamentals_gap_diagnostics` erklaert read-only, ob verbleibende Luecken Profil-, SEC-, Markt- oder Scope-Ursachen haben; `src.fundamentals_overlay_engine` validiert explizite Analyst-Overlays und erzeugt eine Applied-Master-Projektion ohne Mutation des Original-Masters.
4. Watchlist: `src.watchlist_engine` kombiniert Watchlist-Kandidaten mit Scores.
5. Monatsranking: `src.monthly_ranking_engine` erzeugt Monatsranking und Rebalance-Vorschlaege aus Positionen, Scores, Watchlist und Portfolio-Regeln.
6. Reports: `src.build_portfolio_snapshot` und `src.build_monthly_decision_report` erzeugen Markdown aus verarbeiteten Artefakten.
7. Performance und Benchmark: `src.portfolio_history_engine` baut aus expliziten Positions-Snapshots Archiv-/Timeseries-Artefakte; `src.benchmark_history_engine` baut aus expliziten lokalen Benchmark-Zeitreihen ein persistentes Archiv, eine Registry und eine einzelne Performance-kompatible Normalized-Reihe; `src.performance_engine` erzeugt Benchmark-/Performance-Artefakte mit Snapshot-, Perioden- und expliziten Historien-KPIs; `src.multi_benchmark_performance_engine` vergleicht mehrere explizit ausgewaehlte Archiv-/Registry-Benchmark-Symbole gegen dieselbe Portfolio-Zeitreihe.
8. Cost/Tax: `src.cost_tax_archive_engine` kann belegte manuelle oder Dokumentdaten in ein persistentes normalisiertes Archiv mergen; `src.cost_tax_engine` erzeugt daraus bzw. aus direkten Inputs Ledger-, Summary-, KPI- und Report-Artefakte.
9. Dashboard: `src.dashboard_engine` konsolidiert verarbeitete Artefakte in KPI-, Section-, Summary- und Markdown-Ausgaben; `src.dashboard_server` stellt diese Dashboard-CSVs plus bestehende processed Decision-/Coverage-/Ledger-/Timeseries-Artefakte read-only als lokalen localhost-Viewer bereit, ohne neue Finanzlogik, ohne Imputation und mit einem expliziten History-Gate unter 12 Punkten.
10. Persoenlicher Orchestrator: `src.personal_run_engine` fuehrt nur explizit angeforderte Stages in kanonischer Reihenfolge aus und protokolliert Run-Status, Inputs, Outputs, Warnings und Stage-Ergebnisse in Manifest-/Artefakt-Outputs.

## ROADMAP / Spaeter

- Evidence Capture fuer Fundamentals weiter schaerfen, ohne fehlende KPI-Werte zu erfinden oder Sample-Daten still fuer persoenliche Holdings zu nutzen.
- Den operativen Pfad `SEC refresh -> profile seed -> manuelle profile review -> profiled master -> downstream -> gap diagnostics` nur ueber bestehende read-only / auditierbare Zwischenartefakte ausbauen.
- Dashboard-Runbooks nur erweitern, wenn sie aus bestehenden verarbeiteten Artefakten gespeist werden und keine neue Fachlogik einfuehren.
- Performance- und Cost-/Tax-Abdeckung nur dort vertiefen, wo passende Zeitreihen- oder Event-Evidenz vorhanden ist.

## Definition Of Done fuer Patch-Arbeit

- Repo-Reality vor Aenderungen dokumentiert: Branch, HEAD, Worktree-Status und relevante Dateioberflaechen.
- Betroffene Modulgrenzen aus Code, Configs, README und Tests abgeleitet.
- Keine privaten Rohdaten, keine generierten Processed-Artefakte und keine Reports committed.
- Fehlende Daten bleiben sichtbar und werden nicht geraten.
- README-Pfade und CLI-Beispiele bleiben repo-portabel.
- Gezielte Tests und ein praktikabler `unittest`-Basislauf wurden ausgefuehrt oder ein Blocker wurde explizit dokumentiert.
- Nach dem Patch wurde die QA-Aufgabe in `docs/CODEX_TASKS/POST_ITERATION_QA.md` als Review-Schritt angewendet.
