# Forward Experiment Contract v1

## Purpose

This contract defines the boundary between exploratory Forward Validation and a
possible later confirmatory experiment registry. It is contract-first: v1 does
not implement an experiment registry or start a confirmatory evaluation.

## Modes

`EXPLORATORY` produces descriptive diagnostics, design checks, power planning,
and later hypothesis proposals. It cannot establish a confirmed result or
promote policy.

`CONFIRMATORY` would require a separately accepted, locked preregistration and
sufficient real forward data. It is disabled in v1:

```text
confirmatory_registration_enabled = false
```

## Lifecycle

- `REGISTERED`: a complete experiment specification has been recorded before
  observing the primary outcome
- `LOCKED`: human approval freezes the specification and its canonical hash
- `RESOLVED`: the locked outcome window has completed and a human-confirmed
  result exists

These lifecycle names define future semantics only. V1 must not create a real
`CONFIRMATORY` record while the policy flag is false.

## Required future preregistration fields

Every future confirmatory experiment must define before lock:

- hypothesis
- primary outcome
- primary metric
- effect size
- alpha
- power
- sampling unit
- cluster structure
- multiple-testing family
- minimum detectable effect (MDE)
- deterministically calculated required n
- earliest plausible resolution date
- peek policy

`required_n` must come from `src.validation_power`; it must not be manually
invented. Correlation power plans state Pearson or Spearman explicitly and are
labeled `POWER_PLANNING_APPROXIMATION`. Cluster planning has no default ICC.

## Activation gate

Confirmatory registration needs all of:

1. an explicit Human Policy Change,
2. a Power Gate showing sufficient planned real observations,
3. adequate real forward Decision/Trigger history,
4. accepted outcome and clustering definitions,
5. a locked multiple-testing family and peek policy.

No result may be called confirmatory merely because 40-60 triggers exist.

## Multiple testing

Benjamini-Hochberg false discovery rate is the planned method for later defined
hypothesis families. V1 does not implement an ablation zoo. Deflated Sharpe
Ratio is reserved for later genuine strategy/Sharpe selection and is not a
universal multiple-testing method.

## Separation of authority

Exploratory findings can propose later hypotheses. Evidence cannot automatically
become policy. A policy change always requires separate human review and cannot
be applied by a trigger resolver, calibration report, LLM, or scheduler.
