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
- Handoff-ZIPs duerfen explizit allowlistete Patch-Evidenzartefakte aus `data/processed/` und `reports/YYYY-MM-DD/` enthalten, wenn sie fuer externe LLM-Validierung der Datenlage noetig sind; das ist keine Freigabe fuer pauschale Commit-Aufnahme oder historische Output-Ballastdateien.
- Handoff-ZIPs muessen dem einheitlichen [Handoff Contract](../HANDOFF_CONTRACT.md) folgen und die standardisierten `HANDOFF_*` Dateien enthalten; private Raw-Daten, `.git/`, Caches, alte ZIPs und `data/raw/private/` bleiben verboten.
- Externe Review-Patches muessen `outputs/handoffs/latest/HANDOFF_LATEST.zip`, `.sha256` und `_CONTEXT.md` atomisch aktualisieren und die Archive/Latest-Konsistenz pruefen.
- Handoff-QA muss bestaetigen, dass die externe `HANDOFF_LATEST_CONTEXT.md` exakt zur internen `HANDOFF_CONTEXT.md` im ZIP passt, dass Archive/Latest-Hashes gleich sind, dass die SHA256-Datei zum ZIP passt, dass `HANDOFF_VALIDATION.txt` den echten `file_count` ausweist und dass `forbidden_count=0` sowie `nested_zip_count=0` gelten.
- Handoff-QA muss Validation Provenance pruefen: `HANDOFF_VALIDATION.txt` enthaelt die ausgefuehrten Validierungsbefehle oder `self_validation_only`, pass/fail-/Statusinformationen, `sha256_verified`, `context_match`, `latest_archive_hash_match` und `validation_status`.
- Externe Uploads sollen die eindeutig benannten Dateien aus `outputs/handoffs/upload_ready/<upload_bundle_id>/` verwenden. Nicht das generische `HANDOFF_LATEST.zip` hochladen, wenn mehrere Handoffs existieren. ZIP, `_CONTEXT.md` und `.sha256` gehoeren als Trio zusammen.
- Neue Module, Workflow-Stages, generated Artefakte, Handoff-Verhalten oder Website-Mockup-Materialien muessen gegen [Documentation Maintenance](../DOCUMENTATION_MAINTENANCE.md) und [Docs Drift Checklist](DOCS_DRIFT_CHECKLIST.md) geprueft werden.
- Vor Konsolidierungs-Commits muss ein Docs-Drift-Report erzeugt werden; offene Warnungen muessen entweder gefixt oder im Patch-Report akzeptiert werden.
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

## Handoff-Spur

Nach Patches, die externe LLM-Validierung oder reproduzierbare Uebergabe erfordern, muss ein frisches Handoff-ZIP erzeugt werden. Aeltere `compound_income_os_HANDOFF_*.zip` im Repo-Root sollen entfernt werden, sodass nur das aktuelle Handoff-Paket liegen bleibt. Der Export muss einen Forbidden-Entry-Scan mit `0` Treffern bestehen und alle explizit benoetigten Patch-Evidenzartefakte enthalten.
Neue Handoff-ZIPs werden standardmaessig unter `outputs/handoffs/archive/` erzeugt. `outputs/handoffs/latest/HANDOFF_LATEST.zip`, `.sha256` und `_CONTEXT.md` zeigen auf das juengste Paket. Die Latest-Dateien duerfen erst ersetzt werden, nachdem der Archiv-ZIP und ein gestagter Latest-Satz validiert wurden; bei Fehlern bleibt der vorherige Latest-Satz erhalten. Nach erfolgreicher Latest-/Archive-Validierung erzeugt der Exporter zusaetzlich `outputs/handoffs/upload_ready/<upload_bundle_id>/` mit eindeutig benanntem ZIP, Kontext und SHA256-Datei fuer externe LLM-Uploads. Repo-Root-ZIP-Ausgabe ist nur mit explizitem `--output-path` zulaessig.
