# Post-Iteration QA Task

TASK TYPE: POST-ITERATION QA / BUG-HUNT / EVIDENCE-ONLY / MINIMAL-INVASIVE

## Ziel

Pruefe nach jedem Patch, ob der aktuelle Stand echte Regressionen, Vertragsdrift oder Guardrail-Luecken enthaelt. Melde nur belegte Bugs und liefere fuer jeden bestaetigten Bug einen praezisen, minimal-invasiven Patch-Prompt.

## Vorgehen

1. Repo-Reality pruefen:
   - `git status --short --branch`
   - `git rev-parse --abbrev-ref HEAD`
   - `git rev-parse --short HEAD`
   - relevante Diffs und untracked Dateien
2. Betroffene Subsysteme aus Patch-Diff, README, Configs, Tests und CLI-Entry-Points ableiten.
3. Basis-Testlauf ausfuehren, wenn praktikabel:
   - `python -m unittest discover -s tests -p "test_*.py" -v`
4. Gezielte Smoke-/Contract-Pruefungen je betroffenem Subsystem ausfuehren.
5. Artefakte nur pruefen oder erzeugen, wenn die betroffene Pipeline sie wirklich verlangt.

## Bug-Kriterien

Ein Bug ist nur bestaetigt, wenn mindestens eines gilt:

- Ein Test oder Smoke-Run reproduziert ein falsches Verhalten.
- Code, Config, Template oder README widersprechen sich konkret.
- Ein Guardrail wird nachweislich umgangen.
- Ein Artefaktvertrag wird gebrochen.

Keine hypothetischen Problem-Listen ohne Repro oder Datei-Evidenz.

## Pflicht-Checks

- README-Pfade bleiben repo-portabel.
- Keine privaten Rohdaten, Secrets, `.codex_tmp`, `data/processed/` oder `reports/` in Patch-Commits.
- Fehlende Daten werden nicht erfunden.
- Persoenliche Holdings fallen nicht still auf Sample-Fundamentals zurueck.
- Reports werden aus verarbeiteten Artefakten gebaut.
- Dashboard-Arbeit bleibt Konsolidierung.
- Snapshot-Performance wird nicht als vollstaendige Historie dargestellt.
- Cost/Tax ohne Event-Evidenz wird nicht als Full Ledger dargestellt.

## Output

Falls keine Bugs bestaetigt werden:

```text
NO CONFIRMED BUGS
- gepruefte Dateien / Befehle
- Teststatus
- verbleibendes Restrisiko
```

Falls Bugs bestaetigt werden, pro Bug:

```text
ISSUE-XXX
Evidence:
- Datei/Zeile oder reproduzierbarer Befehl

Impact:
- konkreter Vertrags- oder Guardrail-Bruch

Minimal Patch Prompt:
- TASK TYPE
- Ziel
- betroffene Dateien
- Nicht-Ziele
- Acceptance Criteria
- Regressionstests
```

## Git-Spur

QA selbst committen nur, wenn sie dokumentierte QA-Artefakte als Teil einer akzeptierten Governance-Aufgabe erstellt. Bugfix-Patches muessen getrennt bleiben und duerfen keine unrelated Dirty-Files aufnehmen.
