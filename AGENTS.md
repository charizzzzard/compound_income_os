# AGENTS

## Mission

Dieses Repository ist ein lokales Portfolio-Research-System. Es darf keine Orders ausfuehren.

## Kanonische Doku

- [docs/PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md): harte Projektcharta, Scope und Invarianten
- [docs/CONTEXT_AND_ROADMAP.md](docs/CONTEXT_AND_ROADMAP.md): repo-gestuetzter Ist-Zustand, lokale Worktree-Beobachtungen und Roadmap
- [docs/MODULE_CONTRACTS.md](docs/MODULE_CONTRACTS.md): Modulvertraege, Inputs, Outputs und Drift-Risiken
- [docs/architecture/00_META_SYNTHESIS.md](docs/architecture/00_META_SYNTHESIS.md): akzeptierte Meta-Architektur-Synthese
- [docs/architecture/01_TARGET_OS_KERNEL_V1.md](docs/architecture/01_TARGET_OS_KERNEL_V1.md): sechs Kernel-Domaenen des Compound Income OS
- [docs/architecture/03_INVESTMENT_PHILOSOPHY_V1.md](docs/architecture/03_INVESTMENT_PHILOSOPHY_V1.md): Investment-Philosophie und Nicht-Ziele
- [docs/architecture/04_META_REVIEW_LOOP_PROTOCOL.md](docs/architecture/04_META_REVIEW_LOOP_PROTOCOL.md): Architektur-Review- und Codex-Ausfuehrungsgate
- [docs/architecture/05_ARCHITECTURE_BACKLOG.csv](docs/architecture/05_ARCHITECTURE_BACKLOG.csv): priorisierte Architektur-Backlogfolge
- [docs/architecture/06_ADOPTED_DECISIONS.yaml](docs/architecture/06_ADOPTED_DECISIONS.yaml): akzeptierte Architekturentscheidungen
- [docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md](docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md): implementierter Human-Capture- und Append-only-Vertrag
- [docs/policies/LLM_CODEX_OPERATING_POLICY.md](docs/policies/LLM_CODEX_OPERATING_POLICY.md): LLM-/Codex-Operating-Policy
- [docs/CODEX_TASK_TEMPLATE.md](docs/CODEX_TASK_TEMPLATE.md): wiederverwendbares Codex-Task-Template
- [docs/CODEX_TASKS/POST_ITERATION_QA.md](docs/CODEX_TASKS/POST_ITERATION_QA.md): Pflicht-QA nach jedem Patch

## Guardrails

- Nur read-only Datenadapter fuer Broker/API/Dokumente
- Fehlende Daten nie erfinden
- Bei unvollstaendigen Fundamentaldaten konservativ scoren und `REVIEW` oder `MISSING_DATA` setzen
- Raw-Fundamentals-KPIs bevorzugen, Legacy-Teil-Scores aber kompatibel weiter unterstuetzen
- Score-Audit-Artefakte muessen nachvollziehbar zeigen, welche KPI- und Score-Komponenten verwendet wurden
- Persoenliche Holdings duerfen nicht still auf Sample-Fundamentals basieren
- Monatlicher Cash-Zufluss ausschliesslich aus Konfiguration lesen
- CSV- und Markdown-Artefakte deterministisch erzeugen
- Reports nur aus bereits verarbeiteten Artefakten bauen
- Das Dashboard konsolidiert verarbeitete Artefakte und fuehrt keine neue Fachlogik ein
- Sechs-Kernel-OS-Modell, Human-Final-Decision und deterministic Python als Source of Truth respektieren
- Decision Capture und Journal Validation sind implementiert; reale Forward-Daten, Simulation und Backtesting warten weiterhin auf echte Decisions sowie Accounting-/Replay-Fundamente

## Coding-Konventionen

- Python-Standardbibliothek bevorzugen
- Kleine, testbare Module
- Klare Trennung von Import, Normalisierung, Bewertung, Scoring, Ranking und Reporting
- Scores immer auf `0..100` clampen
- Reports nur aus bereits verarbeiteten Artefakten bauen

## Arbeitsregeln fuer Codex

- Vor Aenderungen echte Repo-Reality pruefen: Branch, HEAD, Worktree-Status, betroffene Dateien
- Explizit unterscheiden zwischen getrackter HEAD-Realitaet, beobachtetem Dirty-/Untracked-Worktree und Roadmap
- Keine Produktlogik unter Doku-/Governance-Aufgaben verstecken
- Nach jedem Patch [docs/CODEX_TASKS/POST_ITERATION_QA.md](docs/CODEX_TASKS/POST_ITERATION_QA.md) als Pflicht-Check verwenden
- Git-Disziplin pro Patch: keine unrelated Dirty-Files stagen, keine privaten Rohdaten, keine generierten Processed-/Report-Artefakte
- Bei dirty Worktree nur committen, wenn die staged Diff klar isoliert und fachlich akzeptiert ist

## Datenfluesse

1. `import_broker` normalisiert Broker-/CSV-Daten nach `positions_snapshot.csv`
2. `scoring_engine` kombiniert Positionen und Fundamentaldaten zu `company_scores.csv`
3. `watchlist_engine` rankt Zielkandidaten zu `watchlist_ranked.csv`
4. `monthly_ranking_engine` erzeugt Kaufvorschlaege und `rebalance_proposals.csv`
5. Report-Builder erzeugen Markdown fuer Snapshot und Monatsentscheidung
