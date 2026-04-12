# Codex Task Template

Nutze dieses Template fuer neue Codex-Patches. Entferne Abschnitte nur, wenn sie fuer die konkrete Aufgabe nachweislich nicht relevant sind.

```text
TASK TYPE:

ZIEL:
- Was soll konkret erreicht werden?
- Welche Akzeptanzkriterien muessen am Ende real belegbar sein?

REPO-REALITY ZUERST:
- Branch, HEAD und `git status --short --branch` pruefen.
- Vorbestehend modified/untracked Dateien dokumentieren.
- Relevante Dateien, Tests, Configs und CLI-Entry-Points lesen.
- Explizit unterscheiden:
  1. tracked HEAD repo reality
  2. observed dirty/untracked local worktree reality
  3. planned / later roadmap state

BETROFFENE DATEIEN / SUBSYSTEME:
- Erwartete Module, Configs, Tests und Artefakte nennen.
- Keine erfundenen Module, Befehle oder Pfade verwenden.

GUARDRAILS:
- Keine Orders, kein Auto-Trading, keine Broker-Schreibzugriffe.
- Fehlende Daten nie erfinden.
- Persoenliche Holdings nicht still auf Sample-Fundamentals mappen.
- Reports nur aus verarbeiteten Artefakten bauen.
- Dashboard ist Konsolidierung, keine neue Fachlogik.
- README ist testrelevante Vertragsflaeche.

UMSETZUNG:
- Minimal-invasiver Ansatz.
- Bestehende Modulgrenzen und lokale Patterns bevorzugen.
- Produktcode nur aendern, wenn es fuer die Aufgabe zwingend noetig ist.

VALIDIERUNG:
- Gezielte Tests:
- Relevante bestehende Tests:
- Basislauf, wenn praktikabel:
  python -m unittest discover -s tests -p "test_*.py" -v
- Erzeugte Artefakte oder bewusst nicht erzeugte Artefakte dokumentieren.

VERBOTE:
- Keine privaten Rohdaten, Secrets, Scratch-Dateien oder generierten Reports/Processed-Artefakte committen.
- Keine stillen Fallbacks, keine fuzzy Matches, keine halluzinierten KPI-Werte.
- Keine unrelated Refactors.

GIT-DISZIPLIN:
- Nur eigene, fachlich passende Dateien stagen.
- Bei dirty Worktree nicht committen, wenn Isolation nicht eindeutig ist.
- Commit-Hash, Message und enthaltene Dateien dokumentieren, falls committed wird.

OUTPUT-FORMAT:
- Repo Reality
- Selected Patch
- Validation
- Output Impact
- Open Gaps
```
