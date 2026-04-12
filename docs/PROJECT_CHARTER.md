# Project Charter

## Zweck

`compound_income_os` ist ein lokales, reproduzierbares Portfolio-Research- und Decision-Support-System fuer ein langfristiges Aktienportfolio mit dem Mandat Dividend Growth + Quality Compounders mit wertorientiertem, datengetriebenem Kaufansatz.

Das System verarbeitet explizite lokale Inputs zu deterministischen CSV-Artefakten und Markdown-Reports. Es fuehrt keine Orders aus.

## Nicht-Ziele

- Keine Broker-Orderausfuehrung, kein Auto-Trading und keine stillen Handelsentscheidungen
- Keine erfundenen Fundamentaldaten, Preise, Cashflows, Steuerwerte oder Benchmarks
- Keine Pflichtintegration externer APIs, kein Scraping und keine Live-Datenabhaengigkeit
- Kein Dashboard als neue Fachlogik; Dashboard-Arbeit ist Konsolidierung verarbeiteter Artefakte
- Kein Full-Ledger-Anspruch fuer Cost/Tax ohne belegte Event-Evidenz

## North Star

Jede Pipeline-Stufe soll nachvollziehbar zeigen, welche lokalen Inputs verwendet wurden, welche Daten fehlen, welche konservativen Flags gesetzt wurden und welches verarbeitete Artefakt daraus entstanden ist.

## In Scope

- Broker-/CSV-/lokale Dokument-Inputs read-only normalisieren
- Positionen, Portfolio-Regeln, Fundamentals, Bewertung, Ranking und Reports deterministisch erzeugen
- Fehlende oder unvollstaendige Daten als `REVIEW`, `MISSING_DATA`, `NOT_AVAILABLE` oder `INSUFFICIENT_HISTORY` sichtbar machen
- Sample-/Fixture-Pfade fuer Tests und Demos erhalten
- Persoenliche Runs von Sample-Fundamentals trennen, sobald ein Personal-Fundamentals-Pfad verwendet wird

## Out of Scope

- Orderrouting, Rebalancing-Ausfuehrung oder Broker-Schreibzugriffe
- Steuerberatung, rechtliche Beratung oder ein vollstaendiges steuerliches Nebenbuch ohne Event-Belege
- Stille Datenanreicherung aus externen Quellen
- Breite Refactors ohne direkten Patch-Zweck

## Invarianten

- Fehlende Daten werden nie aufgefuellt oder geraten.
- Monatlicher Cash-Zufluss kommt aus Konfiguration, nicht aus Hardcodes.
- Reports werden aus verarbeiteten Artefakten gebaut, nicht aus privaten Rohdaten.
- Scores werden auf `0..100` begrenzt.
- CSV- und Markdown-Artefakte bleiben deterministisch.
- Private Rohdaten und generierte Processed-/Report-Artefakte gehoeren nicht in Governance-Commits.

## Alignment

Alignment bedeutet in diesem Repo: zuerst die reale Repo- und Worktree-Lage pruefen, getrackte HEAD-Realitaet von lokalen Dirty-/Untracked-Beobachtungen und Roadmap trennen, dann minimal-invasiv gegen die bestehenden Modulgrenzen arbeiten.
