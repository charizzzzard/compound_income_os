# Compound Income OS External LLM Review Packet - Registry Preflight

Dies ist der Einstiegspunkt fuer die externe Delta-Review von Compound Income
OS (CIOS) nach dem Patch:

- commit: `c7a8c64789ad2549ba3e10731cc2dd0fbd864f0a`
- message: `feat: add data source registry validation preflight`
- status: `DATA_SOURCE_REGISTRY_PREFLIGHT_ACCEPTED_WITH_FINDINGS`

## Current Review Head

- project: `compound_income_os`
- canonical_name: `Compound Income OS`
- short_name: `CIOS`
- branch: `main`
- current_handoff_head: `c7a8c64789ad2549ba3e10731cc2dd0fbd864f0a`
- current_handoff_short_head: `c7a8c64`
- bundle_purpose: `external_llm_delta_review_after_data_source_registry_preflight`
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

- Data Source Registry Validation Preflight:
  - `src/data_source_registry_validation.py`
  - `tests/test_data_source_registry_validation.py`
- Data Source Strategy / License Boundary:
  - `docs/architecture/CIOS_DATA_SOURCE_STRATEGY.md`
  - `docs/contracts/DATA_SOURCE_LICENSE_BOUNDARY_CONTRACT.md`
  - `docs/architecture/CIOS_DATA_SOURCE_REGISTRY_TEMPLATE.yaml`
  - `docs/governance/DATA_SOURCE_REVIEW_CHECKLIST.md`
- Governance/status consistency:
  - `docs/architecture/CIOS_FEATURE_STATUS.yaml`
  - `docs/architecture/CIOS_MATURITY_MODEL.yaml`
  - `docs/architecture/CURRENT_KNOWN_GAPS.md`
  - `docs/governance/CIOS_RISK_AND_CONTROL_FRAMEWORK.md`
  - `docs/governance/EXTERNAL_REPRODUCTION.md`
  - `README.md`
  - `docs/CONTEXT_AND_ROADMAP.md`
  - `docs/MODULE_CONTRACTS.md`

## Dirty-State Interpretation

ZIP-internes `HANDOFF_CONTEXT.md` kann `dirty_worktree_present: True` zeigen,
weil `external_review_packet/HANDOFF_LATEST.sha256` und diese externen
Metadaten nach der ZIP-Erzeugung neu geschrieben wurden. Entscheidend ist der
tracked Source State vor Handoff-Erzeugung und der finale Status nach dem
Handoff-Metadatencommit.

## Explicit Non-Scope

Dieses Packet fuehrt nicht ein:

- API-Anbindung
- Scraping oder Web-Crawling
- Provider-Adapter
- produktive Source Registry
- Runtime-Enforcement-Integration
- Broker Parser
- Dashboard
- Replay, Backtesting oder Simulation
- Outcome Attribution
- Portfolio Event Ledger
- Legal-/Commercial-Freigabe
- Investmentlogik
- Buy/Sell Recommendations
- Steuerberechnung
- Scoring-/Ranking-Aenderung
- Portfolio-Regel-Aenderung
- Runtime-LLM-Agentenlogik

## Reviewer Notes

- Der Preflight validiert das Template und konservative Boundary-Regeln.
- Er genehmigt keine realen Provider.
- Er ersetzt keine Legal-/Commercial-Review.
- Er ist nicht in den Personal Run als Runtime-Enforcement integriert.
- Bestehende `configs/data_sources.yaml` und
  `configs/personal_run_data_sources.yaml` bleiben operative lokale Input-
  Configs, keine License Registry.
