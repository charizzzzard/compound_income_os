# CIOS System Constitution

## Canonical Name

The canonical project name is `Compound Income OS`.

The canonical short name is `CIOS`.

Historical or informal variants such as `COS`, `CUS` or other abbreviations are
not authoritative names. They must not be introduced in new contracts, release
metadata or user-facing governance documents unless explicitly documented as
historical context.

## Purpose

CIOS is a local-first, deterministic investment decision-support system for a
long-horizon equity portfolio. It turns reviewed local evidence into auditable
Python artifacts, manifests, reports and review queues for a human final
decision.

CIOS exists to improve process quality, evidence traceability, data freshness
visibility, review discipline and release governance. It does not exist to make
or execute investment decisions.

## Non-Purpose

CIOS is not:

- a broker
- an order-execution system
- an auto-trading system
- an autonomous portfolio manager
- an investment adviser
- a runtime financial-advice LLM agent
- a market prediction engine
- a simulation, backtesting or Monte Carlo system
- an outcome-attribution system
- a tax-advice or legal-advice system
- a commercial product unless a later product/commercial boundary review says so

## Invariant Principles

- `KERNEL_SYSTEM_CONSTITUTION`: System identity and non-purpose must remain
  explicit in every major architecture patch.
- `KERNEL_OPERATING_MODEL`: The human operator is the final acceptance and
  decision authority.
- `KERNEL_TRACEABILITY`: Non-trivial changes must trace to a kernel,
  requirement, known gap, risk control, release gate, data boundary or product
  boundary.
- `KERNEL_RISK_CONTROL`: Risks are not considered controlled without an
  artifact, control, validation gate or accepted non-scope statement.
- `KERNEL_RELEASE_ENGINEERING`: Releases and handoffs are evidence artifacts,
  not substitutes for the committed repo.

## Local-First Principle

CIOS must remain operable from local files and deterministic Python. External
providers, APIs, browser sessions, cloud services or paid data sources may be
added only behind explicit adapter, license and data-boundary contracts.

## Deterministic Execution Principle

For the core pipeline, the same committed code, configs and local inputs should
produce stable artifacts. Runtime randomness, non-deterministic LLM decisions
and hidden network dependencies are not allowed in the decision-support path.

## Evidence-First Principle

Every non-trivial output should show what evidence, config, contract, manifest
or source artifact it used. Missing, stale, unknown or invalid data must remain
visible and must not be converted into confidence.

## Human-In-The-Loop Principle

CIOS can surface review states, candidate rows, missing evidence, stale data and
operator attention reasons. It cannot approve, reject, buy, sell, rebalance or
execute an investment action. The human operator decides outside the system.

## No Broker / No Order Execution Principle

No CIOS patch may introduce broker write access, order routing, order placement,
automatic rebalancing, HTTP-write broker APIs or hidden execution behavior
without a separate authority, regulatory, security and release review. The
current constitution treats those capabilities as out of scope.

## No Automated Investment Advice Principle

Scores, rankings, review queues, dashboard summaries and reports are process
support. They are not personalized legal, tax or investment advice and must not
be presented as automated buy/sell/hold decisions.

## Missing / Stale / Unknown Data Principle

Missing, stale, unknown, invalid or not-applicable data states must remain
machine-visible and report-visible. They must not be silently converted to
`FRESH`, `PASS`, `READY` or equivalent positive states.

## No Silent Source Substitution

No module may silently substitute sample data, unrelated files, stale local
exports or generated placeholders for expected personal inputs. Fallbacks must
be explicit, reviewable and tested.

## No Silent Overwrite Of Accepted Facts

Accepted contracts, append-only journal facts, release metadata and reviewed
human decisions must not be overwritten silently. Ledger-like facts should
prefer append-only updates, explicit supersession or migration records.

## Reproducibility Principle

Validation commands, manifests, artifact indexes, used-inputs rows, checksum
files and handoff metadata are part of the evidence trail. A result without a
reproducible path is not authoritative.

## Data Privacy And Handoff Boundary

Private raw data, credentials, local user paths, user-agent values, private
broker documents and secrets must not enter external handoff packages or
governance commits. Handoff bundles are review packages with controlled
allowlists, not full local worktree snapshots.

## Release Authority Principle

The committed Git repo, accepted governance artifacts, manifests, validation
outputs, release/handoff metadata and the human operator together define release
authority. Chat messages and uncommitted generated text do not.

## External LLM Advisory Principle

External LLMs may review, criticize, red-team and suggest changes. They cannot
accept releases, override deterministic artifacts, approve investment actions or
replace the human operator.

## Product / Commercial / Legal Boundary

CIOS may later become a product candidate only after explicit product boundary,
data license, security, commercial and legal reviews. This constitution does not
assert legal compliance, commercial readiness or suitability for public use.

## Baseline Distinctions

- `meta-baseline complete`: system identity, authority, risk, traceability,
  evolution and maturity rules exist.
- `architecture baseline complete`: kernel contracts and stage boundaries exist
  for a specific architecture area.
- `private operable system`: local workflows are usable by the human operator
  with known gaps.
- `product candidate`: packaging, UX, support, license and safety boundaries
  are reviewed.
- `commercial candidate`: commercial, legal, security, data-license and
  operational controls are reviewed.

`CIOS_META_BASELINE_ACCEPTED` does not mean feature-complete,
product-complete, commercial-ready, investment-ready or legally reviewed.
