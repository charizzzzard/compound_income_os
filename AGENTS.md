# AGENTS

## Mission

Dieses Repository ist ein lokales Portfolio-Research-System. Es darf keine Orders ausfuehren.

## Guardrails

- Nur read-only Datenadapter fuer Broker/API/Dokumente
- Fehlende Daten nie erfinden
- Bei unvollstaendigen Fundamentaldaten konservativ scoren und `REVIEW` oder `MISSING_DATA` setzen
- Monatlicher Cash-Zufluss ausschliesslich aus Konfiguration lesen
- CSV- und Markdown-Artefakte deterministisch erzeugen

## Coding-Konventionen

- Python-Standardbibliothek bevorzugen
- Kleine, testbare Module
- Klare Trennung von Import, Normalisierung, Bewertung, Scoring, Ranking und Reporting
- Scores immer auf `0..100` clampen
- Reports nur aus bereits verarbeiteten Artefakten bauen

## Datenfluesse

1. `import_broker` normalisiert Broker-/CSV-Daten nach `positions_snapshot.csv`
2. `scoring_engine` kombiniert Positionen und Fundamentaldaten zu `company_scores.csv`
3. `watchlist_engine` rankt Zielkandidaten zu `watchlist_ranked.csv`
4. `monthly_ranking_engine` erzeugt Kaufvorschlaege und `rebalance_proposals.csv`
5. Report-Builder erzeugen Markdown fuer Snapshot und Monatsentscheidung
