# Compound Income OS — Vision v1.1

**Post-Review-Konsolidierung. Basis: v1 + externes LLM-Review.**

---

## Versionsänderungen v1.0 → v1.1

| Abschnitt | Änderung |
|---|---|
| 4 | 5 neue Decision-Typen ergänzt (4.9-4.13): Cash-Refill, Rebalance-Review, Corporate Actions, Dividend-Risk, FX-Exposure |
| 4.5 / 4.6 | Stufung eingeführt: vor Phase 2 Ledger nur `*_ATTENTION` (qualitativ), nach Phase 2 `*_REVIEW` (steuerlich quantifiziert) |
| 4.2 | Sparplan-Trigger-Logik präzisiert: SINGLE_ORDER nur bei Kombi aus Drawdown + Valuation + Business-Gate + Portfolio-Fit |
| 5 | Tax-Lot-Schema ergänzt (FIFO statt Durchschnitt, `asset_tax_class`, `loss_bucket_type`, etc.) |
| 6 | Multi-Kernel-Mapping (primary + source kernels) statt Single-Kernel-Zuordnung |
| 7 | `src/platform/` Cross-Cutting-Layer eingeführt; gestufte Einführung über Phasen |
| 8 | Phase-Roadmap unverändert in Reihenfolge, aber `*_ATTENTION` schon in Phase 1 zulassen |
| 9 | "Kein Backtesting" präzisiert: keine renditebasierte Optimierung, aber diagnostische Replay-/Sensitivitäts-Checks erlaubt |
| 9 | Neue Disziplin-Linie: `tax_confidence` Gate für steuerliche Empfehlungen |
| 10 | Zeit-Budget realistischer: 30-40 min Normalfall, 45-90 min bei neuen Holdings / Quartal |
| 10 | Phase-1-Automatisierungen ergänzt: Prefill, Stale-Queue, Reconciliation-Summary |

---

## 0. Lese-Vertrag

Dieses Dokument beschreibt das **Zielbild** nach geplanter Konsolidierung eines existierenden Repos, nicht Greenfield.

**Stand TRACKED_HEAD:**
- 90 src-Module, ~44.000 LOC
- 821 Tests, alle grün
- Six-Kernel-OS-Architektur akzeptiert (`docs/architecture/06_ADOPTED_DECISIONS.yaml`)
- Decision Capture Producer existiert, Journal noch leer

**Ziel v1.1:** Implementierungsfähige Vision nach externem Review. Anschließend: Patch 1 (Konsolidierung).

---

## 1. Vision in einem Satz

Ein lokales, langlaufendes Operating System, das Investment-Entscheidungen **strukturiert, dokumentiert und über Jahre lernfähig macht** — ohne Trades auszuführen, ohne Daten zu erfinden, ohne Black-Box-Optimierung.

Decision-Support, kein Auto-Trader. Lokal, nicht Cloud. Deterministische Python-Logik als Source-of-Truth; LLMs assistieren, entscheiden nicht.

---

## 2. Investment-Philosophie

Drei Säulen: **Dividend Growth**, **Quality Compounders**, **Value Discipline**.

**Decision Principles:**
- No-Action ist eine gültige Entscheidung
- Opportunity Cost ist immer relevant
- Margin of Safety ist Disziplin, nicht Genauigkeit
- Score ist diagnostisches Signal, nicht Entscheidung
- Der menschliche Operator entscheidet final

---

## 3. Operator-Profil

| Merkmal | Wert |
|---|---|
| Region | DACH (Deutschland) |
| Broker | Trade Republic (PDF-/CSV-Import) |
| Kapitalzufluss | 500 EUR / Monat + akkumulierte Dividenden |
| Horizont | Jahre bis Jahrzehnte |
| Mandat | Dividend Growth + Quality Compounders + global diversifizierter Core |
| Steuerregime | DE: KESt 26.375 %, Sparerpauschbetrag 1.000 EUR p.a., Teilfreistellung 30 % bei Aktien-ETFs, separater Aktien-Verlustverrechnungstopf, **FIFO pro Depot** |
| Sparplan-Möglichkeit | Trade Republic Sparpläne (kostenfrei) für ETFs und viele Aktien |
| Zeit-Budget | 30-40 min Monthly Run normal; 45-90 min bei neuen Holdings oder Quartals-Updates |

---

## 4. Entscheidungs-Use-Cases mit konkreten Outputs

### 4.1 Monthly Cash Deployment

**Trigger:** monatlich, 500 EUR + ggf. akkumulierter Cash

**Output:** `monthly_decision_report.md` mit Top 1-3 Kaufkandidaten, Bucket-Drift-Status, Cash-Hold-Empfehlung bei nichts gut genug.

**Operator-Action:** 1-3 Decision-Capture-Einträge, manuelle Ausführung.

### 4.2 Sparplan-Routing

Pro Kaufkandidat im Monthly Decision Report ein `execution_mode`:

```
SAVINGS_PLAN_EXISTING — Betrag zum bestehenden Sparplan addieren
SAVINGS_PLAN_NEW      — neuen Sparplan einrichten
SINGLE_ORDER          — Einzelkauf empfohlen
```

**SINGLE_ORDER nur wenn (alle Bedingungen):**
- `savings_plan_eligible = false` ODER
- (`drawdown_opportunity_score ≥ threshold` AND `valuation_score ≥ buy_gate` AND `business_score ≥ buy_gate` AND `bucket_underweight_gap ≥ material_gap` AND `position_weight_after_buy ≤ cap`) ODER
- `candidate_amount_eur ≥ single_order_min_amount_eur` mit `order_fee_ratio ≤ max_fee_ratio` ODER
- `next_savings_plan_execution_days > max_wait_days`

**Wichtig:** Drawdown allein ist kein Einzelkauf-Trigger. Buy-the-Dip muss durch Valuation + Business-Gate + Portfolio-Fit validiert sein.

**Neues Artefakt:** `data/raw/savings_plan_registry.csv` — manuell gepflegter Spiegel aktiver TR-Sparpläne.

### 4.3 Universe-Tracker / Watchlist-View (Always-On)

Dashboard-Section "Universe": alle getrackten Firmen (Holdings ∪ Watchlist ∪ optional Beobachtungs-Universum) mit aktuellen Scores, Status-Badge, Stale-Marker, Bucket-Zuordnung. Filterbar nach Score, Status, Sektor, Datenstand.

**Akzeptanzkriterium:** bei 300 Assets unter 1 Sekunde lokal filtern.

### 4.4 Trim / Exit bei Investment-Case-Verletzung

Trigger: Position-Cap, Business-Score-Drift, Hard Risk Flag, Dividenden-Kürzung, Thesis `BROKEN`. Output: `portfolio_review.csv` mit `TRIM_REVIEW` / `EXIT_REVIEW`.

### 4.5 Gewinnmitnahme / Profit Taking

**Mindestlogik (gain allein reicht nie):**
```
profit_taking_candidate =
  unrealized_gain_threshold_met
  AND (
    position_cap_breach
    OR valuation_stretched
    OR sector_cap_breach
    OR top10_concentration_breach
    OR business_score_derating
    OR thesis_stale_overdue
  )
```

**Output-Stufung:**

| Bedingung | Output-Typ | Felder |
|---|---|---|
| Vor Phase 2 (kein Event Ledger) | `PROFIT_TAKING_ATTENTION` | qualitativ: Position-Weight, Valuation-Drift-Marker, Business-Score-Trend. **Keine** Steuerberechnung. |
| Ab Phase 2 (Event Ledger vorhanden) | `PROFIT_TAKING_REVIEW` | quantitativ: `unrealized_gain_eur`, `realized_gain_eur_fifo`, `estimated_kest_eur`, `freibetrag_remaining_eur`, `net_after_tax_eur`, `tax_optimal_trim_eur` |

**Disziplin:** `PROFIT_TAKING_REVIEW` ist nur erlaubt mit `tax_confidence = RECONCILED_LEDGER`. Sonst bleibt es `_ATTENTION`.

### 4.6 Verlust-Realisierung mit Steuer-Verrechnung

**Output-Stufung analog zu 4.5:**

| Bedingung | Output-Typ |
|---|---|
| Vor Phase 2 | `LOSS_RISK_ATTENTION` — qualitativ: Investment-Case-Status, unrealized Loss, ohne Steuer-Shield-Berechnung |
| Ab Phase 2 + `tax_confidence = RECONCILED_LEDGER` | `LOSS_REALIZATION_REVIEW` — mit `verlustverrechnung_topf_aktien_eur`, `realized_gains_ytd_aktien_eur`, `estimated_tax_shield_eur` |

**Hintergrund DE (BMF-belegt):** Aktienverluste sind nur gegen Aktiengewinne verrechenbar (eigener Topf, § 20 EStG). FIFO pro Depot ist verbindlich für die Cost-Basis-Bestimmung.

### 4.7 Quartals-Health-Check

Dashboard-Section "Health": Bucket-Drift, Top-10-Konzentration, Sektor-Cap, Multi-Benchmark-Performance, Cost-Quote YTD, Sparerpauschbetrag-Auslastung, Topf-Stand, Vorabpauschale-Vorschau, KPI-Tier-Coverage.

### 4.8 Jährliches Strategy-Review

Ab Jahr 2 (30-50 Decision-Einträge mit Outcome-Daten): Policy-Change-Vorschläge auf Basis echter Outcomes. Manuelles Patchen, kein Auto-Update.

### 4.9 Cash-Refill-Required (NEU)

**Trigger:** Cash unter `min_cash_reserve_eur` ODER unterhalb Bucket-Cash-Floor (5 %)

**Output:** Decision-Type `CASH_REFILL_REQUIRED` mit Empfehlung "kein Buy diesen Monat, Cash auffüllen lassen". Verhindert Buy-Empfehlungen, die Cash-Floor verletzen würden.

**Wichtig:** Auto-Sells für Cash-Refill sind verboten. Cash-Refill passiert über frischen Sparzufluss, nicht über Verkäufe.

### 4.10 Rebalance-Review (NEU)

**Trigger:** Bucket-Drift über Toleranzband UND Cash-only-Rebalancing reicht nicht aus.

**Output:** `REBALANCE_REVIEW` mit:
- **Cash-first-Logik:** Untergewichtetes Bucket bevorzugt mit neuem Cash auffüllen statt Übergewicht verkaufen
- Verkauf nur empfohlen, wenn Drift > 2× Toleranzband UND Steuerwirkung akzeptabel

### 4.11 Corporate-Action-Review (NEU)

**Trigger:** Splits, Spin-offs, Mergers, Quellensteuer-Änderungen, Depotüberträge.

**Output:** `CORPORATE_ACTION_REVIEW` mit Hinweis auf benötigte manuelle Master-/Ledger-Updates.

**Phasen-Zuordnung:** Erst ab Phase 2 vollständig (braucht Event Ledger). Vor Phase 2: manueller Review-Hinweis ohne automatische Cost-Basis-Anpassung.

### 4.12 Dividend-Risk-Review (NEU)

**Trigger (vor Kürzung, nicht erst danach):**
- FCF-Payout-Ratio steigt über Schwelle (z.B. > 90 %)
- Net-Debt/EBITDA Spike (z.B. > 4.0)
- Interest-Coverage-Drop (z.B. < 3.0)
- FCF-Coverage der Dividende fällt unter 1.2

**Output:** `DIVIDEND_RISK_REVIEW` als Pre-Cut-Warnung. Eskaliert zu `EXIT_REVIEW` erst nach tatsächlicher Kürzung. Operator entscheidet, ob präventiv reduzieren oder abwarten.

### 4.13 FX-Exposure-Review (NEU)

**Trigger:** quartalsweise im Health-Check.

**Output:** Exposure-Verteilung in USD / CHF / GBP / sonstige, gegen konfigurierbare Soft-Caps. **Kein Trading-Signal.** Hedging wird bewusst nicht aufgenommen.

---

## 5. Capability-Katalog (mit Tax-Lot-Schema)

**Daten:**
- Trade Republic PDF / Broker-CSV
- Personal Fundamentals Master als zentrale CSV
- Externe Fundamentals via Snapshot-CSV (FMP / SimFin / Stockanalysis / manuell)
- Benchmark-Zeitreihen + Cost/Tax-Ledger via CSV
- **Sparplan-Register** als manuell gepflegte CSV
- **Tax-Lot-Register** (ab Phase 2) als persistente Event-Folge

**Bewertung:** Business-Score, Valuation-Score, Buy-Score (alle 0-100), KPI-Tier-Coverage.

**Portfolio-Regeln:** Bucket-Bänder, Position-Caps, Buy-/Sell-Gates, Profit-Taking-Trigger, Loss-Realization-Trigger.

**Tax-Lot-Schema (Phase 2):**

```
tax_lot_id
depot_id
ticker
isin
acquired_date
acquired_quantity
acquired_price_eur
acquired_fx_rate
fees_eur
fifo_sequence
asset_tax_class: STOCK | ETF_EQUITY | ETF_MIXED | FUND_OTHER | CASH_INTEREST | OTHER
fund_partial_exemption_rate    # 0.30 bei Aktien-ETFs
loss_bucket_type: STOCK | GENERAL | NONE
status: OPEN | CLOSED | PARTIALLY_CLOSED
```

**Tax-State (Phase 3):**

```
freistellungsauftrag_total_eur
freistellungsauftrag_used_ytd_eur
sparerpauschbetrag_remaining_eur
verlustverrechnung_topf_aktien_eur
verlustverrechnung_topf_general_eur
realized_gains_ytd_aktien_eur
realized_gains_ytd_general_eur
vorabpauschale_ytd_eur
foreign_withholding_tax_creditable_eur
basiszins_year                 # BMF-Veröffentlichung pro Jahr
```

**Decision-Loop, Reporting, Dashboard, Replay-Minimum:** wie v1, plus die neuen Decision-Typen aus 4.9-4.13.

---

## 6. Six-Kernel-Mapping (multi-kernel, präzise)

Jede Capability hat einen **primary kernel** (Verantwortung) und **source kernels** (Datenabhängigkeiten). Diese Trennung verhindert Fachlogik-Drift ins Dashboard oder in Report-Builder.

| Capability | Primary | Sources |
|---|---|---|
| Sparplan-Register | 2 (State) | 6 (Policy) |
| Sparplan-Routing | 4 (Decision) | 2, 6 |
| Universe-View | 3 (Research) | 1, 2, Dashboard |
| Profit-Taking-Review | 4 (Decision) | 2 (Ledger), 6 (Policy) |
| Loss-Realization-Review | 4 (Decision) | 2 (Ledger), 6 (Policy) |
| DE-Tax-Töpfe | 2 (Accounting) | 6 (Policy) |
| Cash-Refill | 4 (Decision) | 2 (State) |
| Rebalance-Review | 4 (Decision) | 2, 6 |
| Corporate-Actions | 2 (Accounting) | 1 (Identity), 4 |
| Dividend-Risk | 3 (Research) | 1 (Evidence), 4 |
| FX-Exposure | 5 (Benchmark/Outcome) | 2 (State) |

---

## 7. Schlanke Modul-Architektur (mit Cross-Cutting-Layer)

```
src/
├── platform/                          # NEU: Cross-Cutting-Foundation
│   ├── schema_registry.py             # Phase 0/1: versionierte CSV-Schemas
│   ├── validation.py                  # Phase 0/1: Enum/Required-Column Checks
│   ├── artifact_io.py                 # Phase 0/1: atomic writes, deterministic CSV
│   ├── idempotency.py                 # Phase 2: stabile Row-Keys, Merge-Policies
│   ├── run_logging.py                 # Phase 1: structured run logs
│   ├── money.py                       # Phase 2: Decimal, FX, Rounding-Policy
│   ├── time_policy.py                 # Phase 2: run_date, stale_thresholds
│   └── tax_lot_policy.py              # Phase 2: FIFO-Logik, asset_tax_class
│
├── common.py                          # bleibt klein, nur Path-Helpers
├── data_source_registry.py
│
├── import/                            # 18 Module Core Pipeline
│   ├── import_broker.py
│   ├── normalize_positions.py
│   └── traderepublic_documents.py
│
├── master/
│   ├── fundamentals_engine.py
│   ├── fundamentals_master.py
│   ├── fundamentals_evidence_engine.py
│   ├── fundamentals_evidence_apply.py
│   ├── fundamentals_overlay_engine.py
│   ├── fundamentals_profile_engine.py
│   ├── fundamentals_gap_diagnostics.py
│   ├── fundamentals_snapshot_ingestion.py
│   └── company_master.py
│
├── score/
│   ├── scoring_engine.py
│   ├── valuation_engine.py
│   └── personal_score_audit_provenance.py
│
├── decide/
│   ├── portfolio_rules.py
│   ├── portfolio_review.py
│   ├── watchlist_engine.py
│   ├── monthly_ranking_engine.py
│   ├── savings_plan_registry.py        # NEU Phase 1
│   ├── savings_plan_routing.py         # NEU Phase 1
│   ├── cash_refill_review.py           # NEU Phase 1
│   ├── rebalance_review.py             # NEU Phase 1
│   ├── corporate_action_review.py      # NEU Phase 2
│   ├── dividend_risk_review.py         # NEU Phase 1
│   ├── profit_taking_attention.py      # NEU Phase 1 (qualitativ)
│   ├── profit_taking_review.py         # NEU Phase 3 (steuerlich)
│   ├── loss_risk_attention.py          # NEU Phase 1 (qualitativ)
│   ├── loss_realization_review.py      # NEU Phase 3 (steuerlich)
│   └── personal_decision_state_capture.py
│
├── observe/
│   ├── performance_engine.py
│   ├── benchmark_history_engine.py
│   ├── portfolio_history_engine.py
│   ├── portfolio_event_ledger.py       # NEU Phase 2
│   ├── cost_tax_engine.py              # erweitert um Töpfe Phase 3
│   ├── fx_exposure_engine.py           # NEU Phase 1
│   ├── personal_kpi_tier_coverage.py
│   ├── personal_missing_kpi_closure_report.py
│   └── personal_readiness_status.py
│
├── report/
│   ├── build_portfolio_snapshot.py
│   └── build_monthly_decision_report.py
│
├── dashboard/
│   ├── dashboard_engine.py
│   └── dashboard_server.py
│
├── orchestrate/
│   └── personal_run_engine.py
│
└── ops/
    └── handoff_zip_export.py
```

**~50 Module nach allen Phasen** (33 Konsolidiert + ~17 neue über Phasen 1-3 verteilt + 8 platform/-Module gestuft eingeführt).

**Archiviert:** `_archive/sec/` (26 SEC-Module), `website/` (separates Lifecycle).

---

## 8. Roadmap mit Capability-Mapping

| Phase | Dauer | Neue Capabilities | Was du danach kannst |
|---|---|---|---|
| **0 — Konsolidierung** | 2-3 Tage | platform/: `schema_registry`, `validation`, `artifact_io` | Schlankes Repo, Foundation für Schema-Migration |
| **1 — Operations + Always-On** | 4-6 Wochen | Sparplan-Register, Sparplan-Routing, Universe-Dashboard, Cash-Refill, Rebalance-Review, Dividend-Risk, FX-Exposure, **Profit-Taking-ATTENTION + Loss-Risk-ATTENTION** (qualitativ), Decision-Capture-Prefill, Stale-Queue, `run_logging` | Voll einsetzbarer Monthly Run, Always-On Watchlist, qualitative Pre-Warnungen |
| **2 — Portfolio Event Ledger** | 6-8 Wochen | Event Ledger (Trades / Dividenden / Steuern / Kosten als Events), Cost-Basis FIFO, Tax-Lots, Corporate Actions, `money.py`, `time_policy.py`, `tax_lot_policy.py`, `idempotency.py` | Echte Yield-on-Cost, echte realisierte Gewinne, Replay |
| **3 — Tax-aware Profit-Taking + Loss-Realization** | 3-4 Wochen | `PROFIT_TAKING_REVIEW`, `LOSS_REALIZATION_REVIEW` mit `tax_confidence=RECONCILED_LEDGER`, DE-Töpfe, Sparerpauschbetrag-Tracking, Vorabpauschale | Steueroptimierte Trim-/Loss-Empfehlungen |
| **4 — Decision Benchmarking + Outcome Review** | nach 6 Mon. Daten | Jede Decision vs. Benchmark-Alternative, descriptive Outcome, Mini-Diagnostik | Lernfähig |
| **5 — Strategy Feedback + Policy Change** | nach 12-18 Mon. | Policy-Change-Vorschläge | Disziplinierte Evolution |
| **6 — Erweiterte Faktoren (optional)** | offen | News / Insider / 13F / Management / Dilution als neue Evidence-Tiers | Reichere Fundamentals |

**Phasen-Logik:** Phase 1 liefert qualitative `*_ATTENTION` Outputs für Profit-Taking / Loss-Risk. Erst Phase 3 (nach Phase 2 Event Ledger) liefert steueroptimierte `*_REVIEW` Outputs.

---

## 9. Disziplin-Linien

**Hart:**
- **Kein renditebasiertes Backtesting, keine Optimierung, kein Monte Carlo vor Phase 4.** Erlaubt vor Phase 4: Score-Verteilungs-Diagnostik, Schwellen-Sensitivität ohne Returns, Stale-Data-Diagnostik, Factor-Coverage-Reports, historisches Schema-Replay, Rule-Explainability-Tests. Verboten: Gewichtsoptimierung auf historische Returns, Alpha-Claims, Wealth-Path-Simulation, Auto-Change von Scoring-Gewichten.
- Kein Runtime-LLM im Core-Pfad — LLM ist Reviewer + Code-Generator, nicht Producer
- Kein Auto-Trading, keine Broker-Schreibzugriffe
- Keine Imputation fehlender Daten — `MISSING_DATA` bleibt sichtbar
- Keine externe API-Abhängigkeit im Core — alles lokal, alles per CSV
- Kein Steuerberatungsanspruch — Empfehlungen, keine Beratung
- Sparplan-Register ist read-only Spiegel — kein automatisches Anlegen/Anpassen bei TR
- Profit-Taking ist regelbasiert, nicht reaktiv-paranoid — Trigger explizit konfiguriert
- **`tax_confidence` Gate:** Steuerliche Empfehlungen (Profit-Taking-Review, Loss-Realization-Review) nur mit `tax_confidence = RECONCILED_LEDGER`. Bei `PARTIAL_LEDGER` oder `SNAPSHOT_ONLY` nur qualitative `*_ATTENTION`-Outputs ohne EUR-Beträge.
- **Auto-Sells für Cash-Refill verboten** — Cash kommt aus frischem Zufluss, nicht aus Verkäufen
- **FX-Hedging nicht im Scope** — FX-Exposure wird gemessen und berichtet, nicht gemanagt

---

## 10. Operator-Workflow

```
Standard Monthly Run (30-40 min):
1. TR-Depot/Konto-PDF runterladen, raw/ ablegen           (5 min)
2. personal_run_engine ausführen (alle Stages)             (1 min)
3. Stale-Queue prüfen — was an Fundamentals upgedatet      (5-10 min)
   werden muss (nicht alles, nur Blocker)
4. Dashboard öffnen, Universe + Decision Report lesen     (5 min)
5. 1-3 Decision-Capture-Einträge (Prefill aus Report)     (5 min)
6. Bei TR ausführen (Sparplan anpassen / Einzelorder)     (5 min)

Erweitert (45-90 min, bei neuen Holdings oder Quartal):
+ Fundamentals-Snapshot pflegen + Review-Approvals         (15-30 min)
+ Corporate Actions oder Tax-Events einpflegen             (10-15 min)
+ Quartals-Health-Check + FX-Exposure prüfen               (10 min)
```

**Phase-1-Automatisierungen, die den Standardlauf konstant halten:**
- `decision_capture_prefill_from_monthly_report` — vorbefüllter CLI/Form-Modus
- `stale_data_queue` — nur Blocker prüfen statt Full-Pflege
- `savings_plan_registry_validation` — Drift TR ↔ Register flaggen
- `broker_import_reconciliation_summary` — Diff zu Vor-Snapshot
- Monthly Agenda Page: `TOP_ACTIONS`, `BLOCKERS`, `REQUIRED_DECISIONS`
- No-Action-Capture-Shortcut

---

## 11. Anhang: Repo-Referenzen

- Pipeline: `docs/CONTEXT_AND_ROADMAP.md`
- Module Contracts: `docs/MODULE_CONTRACTS.md`
- Adopted Decisions: `docs/architecture/06_ADOPTED_DECISIONS.yaml`
- Investment-Philosophy: `docs/architecture/03_INVESTMENT_PHILOSOPHY_V1.md`
- LLM/Codex Policy: `docs/policies/LLM_CODEX_OPERATING_POLICY.md`
- Decision Capture Contract: `docs/contracts/DECISION_STATE_CAPTURE_CONTRACT_V2.md`
- Architecture Backlog: `docs/architecture/05_ARCHITECTURE_BACKLOG.csv`
- Scoring: `configs/scoring_weights.yaml` + `configs/fundamentals_score_rules.yaml`
- Portfolio-Regeln: `configs/portfolio_rules.yaml`

**DE-Tax-Referenzen (externer Review):**
- § 20 EStG (Aktien-Verlustverrechnung): gesetze-im-internet.de
- EStH 2025 Sparer-Pauschbetrag + FIFO-Anhang 19/II: BMF
- BMF-Schreiben 13.01.2026 Basiszins Vorabpauschale (3.20 % für 2026)
- § 20 InvStG (Teilfreistellung 30 % bei Aktien-ETFs)

---

*v1.1, post external review. Ready for Patch 1 (SEC-Archivierung + Website-Separierung + platform/-Foundation).*
