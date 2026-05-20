# Compound Income OS External LLM Review Packet - Meta + Data Source Governance

Dies ist der Einstiegspunkt fuer die externe LLM-Review von Compound Income OS
(CIOS) nach den beiden Governance-Kernel-Patches:

1. Final Meta-System Baseline / Governance Constitution / Architecture Closure
2. Data Source Strategy & License Boundary

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- current_handoff_head: `8d6a1fc54480ed1ed2cb22d6508ce0228c3c51af`
- current_handoff_short_head: `8d6a1fc`
- current_patch_context: `Meta Governance Baseline + Data Source Strategy / License Boundary`
- handoff_purpose: `external_llm_validation_after_meta_governance_and_data_source_license_boundary`
- meta_baseline_commit: `10082d6d6ad16febe7bb2e500776b08f7bb38103`
- data_source_license_boundary_commit: `8d6a1fc54480ed1ed2cb22d6508ce0228c3c51af`
- canonical_review_bundle: `external_review_packet/HANDOFF_LATEST.zip`
- canonical_checksum: `external_review_packet/HANDOFF_LATEST.sha256`
- canonical_context: `external_review_packet/HANDOFF_LATEST_CONTEXT.md`

## Source-of-Truth / Precedence

Bei Konflikten gilt diese Reihenfolge:

1. `external_review_packet/00_READ_ME_FIRST.md`
2. `external_review_packet/HANDOFF_LATEST_CONTEXT.md`
3. `external_review_packet/HANDOFF_LATEST.zip`
4. `external_review_packet/HANDOFF_LATEST.sha256`
5. historische Reports nur als Kontext

ZIP-internes `HANDOFF_CONTEXT.md` ist generischer Exporter-Kontext. Wenn es mit
dieser externen Kontextdatei kollidiert, gewinnen die externen Dateien fuer
Head, Scope, SHA, Precedence und Dirty-State-Interpretation.

## Review Scope

Reviewer sollen insbesondere pruefen:

- Meta-Governance Baseline:
  - `docs/governance/CIOS_SYSTEM_CONSTITUTION.md`
  - `docs/governance/CIOS_OPERATING_MODEL.md`
  - `docs/governance/CIOS_RISK_AND_CONTROL_FRAMEWORK.md`
  - `docs/governance/CIOS_TRACEABILITY_STANDARD.md`
  - `docs/governance/CIOS_EVOLUTION_GUARDRAILS.md`
  - `docs/governance/CIOS_FINAL_META_BASELINE_ACCEPTANCE.md`
  - `docs/architecture/CIOS_META_ARCHITECTURE.md`
  - `docs/architecture/CIOS_MATURITY_MODEL.yaml`
- Data Source Strategy / License Boundary:
  - `docs/architecture/CIOS_DATA_SOURCE_STRATEGY.md`
  - `docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md`
  - `docs/architecture/CIOS_DATA_SOURCE_REGISTRY_TEMPLATE.yaml`
  - `docs/governance/DATA_SOURCE_REVIEW_CHECKLIST.md`
- Cross-reference and governance consistency:
  - `README.md`
  - `docs/CONTEXT_AND_ROADMAP.md`
  - `docs/MODULE_CONTRACTS.md`
  - `docs/architecture/CIOS_CURRENT_SYSTEM_MAP.md`
  - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
  - `docs/architecture/CURRENT_KNOWN_GAPS.md`
  - `docs/governance/EXTERNAL_REPRODUCTION.md`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` und diese externen
Metadaten nach der ZIP-Erzeugung neu geschrieben wurden. Das ist eine
Handoff-Artefakt-Regeneration, kein Hinweis auf nicht committete Patch-Source-
Aenderungen.

## Explicit Non-Scope

Dieses Packet fuehrt nicht ein:

- Investmentlogik
- API-Anbindung
- Scraping oder Web-Crawling
- Provider-Integration
- Broker-Parser
- Runtime Source Registry Enforcement Logic
- Dashboard
- Replay, Backtesting oder Simulation
- Outcome Attribution
- Portfolio Event Ledger
- Steuerberechnung
- rechtliche Bewertung oder Commercial-Readiness-Behauptung
- Kauf-/Verkaufsempfehlungen
- Runtime-LLM-Agentenlogik
- Scoring-/Ranking-Aenderung
- Portfolio-Regel-Aenderung

## Reviewer Notes

- CIOS ist nicht feature-complete, product-complete oder commercial-ready.
- Die Meta-Baseline akzeptiert nur die Governance-Definition, nicht das
  Produktsystem.
- Data Source Strategy und License Boundary sind Contracts/Governance. Sie sind
  keine Provider-Freigabe, keine Rechtsberatung und keine Commercial-Freigabe.
- Fehlende private/raw/provider Daten duerfen nicht aus dem Handoff inferiert
  werden.
