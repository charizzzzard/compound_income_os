# CIOS Forward Validation v1

## Status and purpose

Forward Validation v1 starts the smallest scientifically defensible forward
learning loop for Compound Income OS:

```text
existing human Decision
  -> 2-5 falsifiable forward claims
  -> Human Lock
  -> time passes
  -> deterministic Due Scan
  -> resolution proposal
  -> Human Confirm
  -> descriptive calibration / Brier / design diagnostics
  -> later hypothesis generation
```

The current local Decision Capture ledger contains no real decision rows.
Therefore the initial operational status is:

```text
operational_forward_validation_status = READY_FOR_FIRST_REAL_DECISION
```

It is not `VALIDATED`. No decision, trigger lock, or resolution is created on
behalf of the operator by this architecture or its deterministic runtime.

## Scientific boundary

The permanent evidence ladder is:

```text
DISCOVERY -> EVIDENCE -> POLICY
```

No stage promotes itself. Discovery can generate later hypotheses. Evidence
requires pre-specified forward observations and review. Policy change requires a
separate human decision. Forward Validation v1 produces only `EXPLORATORY`
diagnostics.

```text
confirmatory_registration_enabled = false
```

Activating confirmatory work later requires a Human Policy Change, a satisfied
Power Gate, and sufficient real forward data. V1 neither registers nor evaluates
a real confirmatory experiment.

## Forward-only LLM boundary

Historical data can later support deterministic quantitative research when its
point-in-time and replay quality is adequate. Historical LLM/Codex
investment-skill evaluation must not be presented as evidence of future LLM
forecast skill: a model may have learned later events parametrically. LLM
incremental value is therefore measured primarily forward-only, against locked
claims and frozen contemporaneous context.

LLMs may propose claims or resolution candidates. They do not lock claims,
confirm resolutions, create investment decisions, or promote policy. There is no
runtime LLM dependency in the deterministic pipeline.

## Unit, clustering, and power

The raw observation unit is a trigger. Dependence is hierarchical:

```yaml
analysis:
  unit: trigger
  cluster_keys:
    - decision_month
    - decision_id
```

Reports retain `raw_trigger_n`, `decision_count`, `decision_month_count`, and the
triggers-per-decision distribution. No ICC is assumed. Until a defensible
empirical estimate exists:

```text
empirical_icc_status = NOT_ESTIMATED
```

ICC values 0.1, 0.3, 0.5, and 0.7 may be displayed only as labeled
`SENSITIVITY_SCENARIO` calculations. They are not estimates. Mean and
correlation planning is implemented in `src.validation_power` and labeled
`POWER_PLANNING_APPROXIMATION`, not an exact inferential test.

## Trigger design and selection diagnostics

Each decision can have two to five locked triggers. Every trigger must be
material, decision-relevant, future-facing, falsifiable, and deterministically
resolvable. Tautologies, already-known facts, unfalsifiable narratives, and
claims without a resolution rule are rejected.

CIOS does not force artificial 50% claims. It also monitors whether claims have
collapsed into an easy high-probability set. Portfolio-level diagnostics include
the probability histogram, share above 0.90, share from 0.35 through 0.75, and
claim-type distribution. Persistent concentration can produce
`TRIGGER_DESIGN_REVIEW`; it does not synthesize counterclaims.

Selling a position, removing an asset from a watchlist, or later changing a
decision does not delete or censor the company/thesis trigger. A corporate event
is `UNRESOLVABLE_CORPORATE` only when it actually prevents the locked
measurement.

## Resolution and descriptive outputs

Final resolution states are `RESOLVED_TRUE`, `RESOLVED_FALSE`,
`UNRESOLVABLE_DEFINITION`, and `UNRESOLVABLE_CORPORATE`. `OVERDUE` is a dynamic
queue condition, never a final resolution. An overdue trigger can still be
resolved when the source document becomes available later.

Only true/false resolutions enter Brier and calibration calculations. The Brier
score is `(probability_holds - y)^2`, with `y=1` for true and `y=0` for false.
Unresolvable cases are reported separately and never coerced to a binary
outcome. Binomial intervals use Wilson intervals and always show `n`, estimate,
lower bound, and upper bound.

The deterministic report also exposes final and binary resolution counts,
distinct resolved decisions, raw active trigger/decision/decision-month cluster
counts, open and overdue rates, unresolvable rate, probability-bin counts,
observed and predicted bin rates, triggers-per-decision distribution, claim-type
distribution, and probability-mix diagnostics. Superseded rows remain in ledger
history but are not treated as active open/due claims. No guessed ICC or
effective sample size is emitted.

Small samples are labeled:

```text
DESCRIPTIVE_ONLY
INSUFFICIENT_FOR_CONFIRMATORY_INFERENCE
```

First diagnostics are not a validated calibration model. Reports must not claim
`validated`, `proven`, `statistically confirmed`, `alpha`, or `predictive edge`
unless a future explicit gate has actually been satisfied.

## Tamper evidence and local operation

Locked trigger and confirmed resolution ledgers are append-only and use an
explicit canonical-record schema version. Hash chains are tamper-evident, not
tamper-proof. Because `data/processed/` is git-ignored, a tracked anchor index may
contain only ledger name, row count, head hash, schema version, Git HEAD, and
timestamps—never personal decision content.

The selected index is `audit/forward_validation/ledger_anchors.jsonl`. It starts
empty and is appended only by an explicit operator command after ledger-chain
verification. The same ledger head is not duplicated. `data/processed/` is
rejected as an anchor location. A later valid append is distinguished from an
anchor mismatch by verifying that the anchored head is still the current
ledger prefix.

Signed Git tags are optional human-operated history checkpoints only when local
signing is already configured. They are a cryptographically signed history
checkpoint, not an immutable external timestamp. External notary/timestamp
services are `OUT_OF_SCOPE_V1`.

Automation is limited to deterministic, idempotent due scans, descriptive
reports, and tests. Trigger approval, resolution confirmation, investment
decisions, and policy promotion remain human actions.

## OUT_OF_SCOPE_V1

- historical LLM backtesting or historical Codex investment-skill validation
- walk-forward optimization or a point-in-time fundamentals warehouse
- strategy backtesting, alpha claims, Sharpe optimization, or Deflated Sharpe as
  a universal multiple-testing method
- automated policy optimization or promotion
- regime switching, HMM, gradient-boosted trees, random forests, neural
  networks, Bayesian ensembles, dynamic factor weights, or ensemble learning
- Champion/Challenger runtime
- automatic investment decisions, trigger approval, or trigger resolution
- broker/order integration
- paper-portfolio simulation and decision-level benchmark return attribution
- external timestamp/notary service

For later hypothesis families, Benjamini-Hochberg FDR is the planned
multiple-testing method. It is documented only; v1 does not build an ablation or
hypothesis zoo.
