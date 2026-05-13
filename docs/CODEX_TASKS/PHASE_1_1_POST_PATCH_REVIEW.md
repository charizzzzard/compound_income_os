TASK TYPE:
REVIEW / AUDIT-ONLY / NON-MUTATING

PROJECT:
compound_income_os

ROLE:
External repository reviewer.

LANGUAGE:
Report in German. Audit commands and findings in their natural shell/code form.

CONTEXT:
Phase 1.1 was implemented in three commits after Patch 2.4 baseline (final head 7f2d20a).
Reported final head for Phase 1.1: bb49a59.
Reported final test count: 545 OK.

Phase 1.1 was supposed to deliver only:
- savings_plan_registry read-only data layer
- dashboard universe section (read-only consolidation)
- savings_plan stage in personal_run_engine using existing --stage repeated CLI pattern
- doc updates (README, MODULE_CONTRACTS, CONTEXT_AND_ROADMAP, ARCHITECTURE_BACKLOG)

This review must run before Phase 1.2 (Sparplan Routing) is started.
Do not implement anything. Do not modify any file. Produce only the audit report.

OBJECTIVE:
Verify that Phase 1.1 patched repo state is:
- within declared read-only scope
- did not introduce routing, scoring, portfolio-rule, watchlist, monthly-ranking,
  Personal-Meta, broker-write, or external-HTTP changes
- preserves header order in written CSV outputs
- documents Pipeline-Phase correctly
- has clean test distribution and reproducible smoke tests
- contains no private/raw data in committed files

==================================================================
SECTION 1 — Repo Reality
==================================================================

Run and record:
- git rev-parse --abbrev-ref HEAD                            (expected: main)
- git rev-parse --short HEAD                                 (expected: bb49a59)
- git status --short --branch                                 (expected: clean)
- git log --oneline -10                                       (last 10 commits)

==================================================================
SECTION 2 — Commit Sequence Verification
==================================================================

Verify Phase 1.1 commit chain:

git log --oneline d39a26a..bb49a59

Expected three commits with messages:
- Phase 1.1a: add savings plan registry layer
- Phase 1.1b: add dashboard universe section
- Phase 1.1c: integrate savings plan stage and update docs

Record actual commit hashes for 1.1a and 1.1b (not just final 1.1c=bb49a59).
Do not trust hashes from any previous report; recompute from git log.

==================================================================
SECTION 3 — New Files Verification
==================================================================

Expected new files (must exist):
- configs/savings_plan_schema.yaml
- data/raw/savings_plan_registry.csv
- src/savings_plan_registry.py
- tests/test_savings_plan_registry.py
- tests/test_dashboard_engine_universe_section.py

Verify via:
- ls -la <each path>
- wc -l src/savings_plan_registry.py                          (sanity check size; report)
- For data/raw/savings_plan_registry.csv:
    - wc -l                                                   (expected: 1; header only)
    - head -1                                                  (expected stable schema order:
        ticker,isin,broker,instrument_name,monthly_amount_eur,frequency,
        execution_day_of_month,active,started_at,last_modified,notes)

==================================================================
SECTION 4 — Changed Files Verification
==================================================================

Expected changed files in Phase 1.1 (and only these in src/, tests/, docs/, README):

src/dashboard_engine.py
src/dashboard_server.py
src/personal_run_engine.py
tests/test_dashboard_server.py
tests/test_personal_run_engine.py
README.md
docs/MODULE_CONTRACTS.md
docs/CONTEXT_AND_ROADMAP.md
docs/architecture/05_ARCHITECTURE_BACKLOG.csv

Verify via:
- git diff --name-only d39a26a..bb49a59 | sort > /tmp/phase11_changed.txt
- compare with expected list above and report deltas (extra or missing)

==================================================================
SECTION 5 — Negative-File Verification (CRITICAL)
==================================================================

Phase 1.1 must NOT have touched these. Run and assert empty output (record exactly):

git diff --name-only d39a26a..bb49a59 | grep -E \
  'src/(scoring_engine|valuation_engine|monthly_ranking_engine|watchlist_engine|portfolio_rules|portfolio_review|fundamentals_)' || echo OK

git diff --name-only d39a26a..bb49a59 | grep -E \
  'configs/(scoring_weights|portfolio_rules|watchlist|fundamentals_)' || echo OK

git diff --name-only d39a26a..bb49a59 | grep -E \
  '_archive/' || echo OK

git diff --name-only d39a26a..bb49a59 | grep -E \
  'website/' || echo OK

git diff --name-only d39a26a..bb49a59 | grep -E \
  'personal_(artifact|core_kpi|dividend|evidence_applied|kpi_provenance|kpi_tier|missing_kpi|monthly_action|private_input|profile_review|score_audit|valuation_input|watchlist_input)' || echo OK

git diff --name-only d39a26a..bb49a59 | grep -E \
  'src/platform/artifact_io\.py' || echo OK

(The last one ensures the write_csv_atomic header-sorting contract was not silently
broken.)

Any non-OK output is a scope violation and must be documented as such.

==================================================================
SECTION 6 — Test Distribution Verification
==================================================================

Run:
- python -m unittest discover -s tests -p "test_*.py" -v 2>&1 | tail -3

Expected: 545 tests, OK, skipped tolerated (record exact count).

Sub-distributions to verify:
- python -m unittest tests.test_savings_plan_registry -v 2>&1 | tail -3
  (expected: >=11 tests)
- python -m unittest tests.test_dashboard_engine_universe_section -v 2>&1 | tail -3
  (expected: >=12 tests)
- python -m unittest tests.test_personal_run_engine -v 2>&1 | tail -3
  (expected baseline + 2-4 new)
- python -m unittest tests.test_dashboard_server -v 2>&1 | tail -3
  (expected baseline + 1-2 new universe-related tests, or unchanged if not strictly required)
- python -m unittest tests.test_dashboard_engine -v 2>&1 | tail -3
  (must remain unchanged or only additive)
- python -m unittest tests.test_platform_artifact_io -v 2>&1 | tail -3
  (must remain unchanged — write_csv_atomic contract untouched)

Compute:
  baseline 518 + new_savings_plan + new_universe + new_run_integration
  must approximately equal 545. Reconcile any discrepancy.

==================================================================
SECTION 7 — Schema-Order Header Verification (CRITICAL)
==================================================================

Vision v1.2 + Phase 1.1 v2 task explicitly required schema-order headers in the
new CSV outputs. Verify by running a header-only smoke-export and inspecting:

mkdir -p /tmp/phase11_review

python -m src.savings_plan_registry \
  --input data/raw/savings_plan_registry.csv \
  --summary-output /tmp/phase11_review/sp_summary.csv \
  --report-output /tmp/phase11_review/sp_report.md

head -1 /tmp/phase11_review/sp_summary.csv

Expected header order (schema-order, not alphabetical):
row_count,active_count,inactive_count,total_monthly_eur,next_execution_day,warning_count,drift_warnings,data_quality_flag

(If actual order differs, that is a regression of the schema-order requirement.)

For Universe section:

python -m src.dashboard_engine --help                          (confirm --universe-output exists)

If repo has sample inputs reachable via existing stage, run:
python -m src.personal_run_engine --stage dashboard
(or whatever stage produces the universe section)

Then:
head -1 data/processed/dashboard_universe_section.csv

Expected header order:
ticker,instrument_name,sector,bucket,sleeve,business_score,valuation_score,buy_score,
watchlist_status,savings_plan_active,last_score_update_date,stale_marker,data_quality_flag

Any deviation from this exact order is a regression.

==================================================================
SECTION 8 — Empty-State Behavior
==================================================================

Verify that the layer behaves gracefully on minimal inputs:

- python -m src.savings_plan_registry --input data/raw/savings_plan_registry.csv \
    --summary-output /tmp/phase11_review/sp_empty.csv \
    --report-output /tmp/phase11_review/sp_empty.md

  Expected:
  - exit code 0
  - sp_empty.csv exists, header + one data row with active_count=0, total_monthly_eur=0
    (or whatever the documented empty-state row format is)
  - sp_empty.md contains an EMPTY_STATE marker or equivalent documented signal

- python -m src.personal_run_engine --stage savings_plan
  Expected: stage succeeds against header-only registry, manifest entries recorded.

==================================================================
SECTION 9 — CLI Smoke Tests
==================================================================

Run and capture exit codes + first lines:

python -m src.savings_plan_registry --help
python -m src.dashboard_engine --help
python -m src.dashboard_server --help
python -m src.personal_run_engine --help
python -m src.scoring_engine --help

Verify:
- personal_run_engine --help shows "savings_plan" in --stage choices
- personal_run_engine --help still uses "--stage" (append) and NOT "--stages" or "--skip-stages"
- dashboard_engine --help shows the new --universe-output option
- scoring_engine --help unchanged (no new flags)

==================================================================
SECTION 10 — Docs Consistency
==================================================================

Verify documentation reflects read-only/no-routing scope:

- grep -nE "Sparplan|savings_plan" README.md                     (must mention read-only)
- grep -nE "Routing|routing|recommendation" README.md             (must NOT promise routing for Phase 1.1)
- grep -nE "savings_plan" docs/MODULE_CONTRACTS.md                (must have row for savings_plan_registry)
- grep -nE "Universe" docs/MODULE_CONTRACTS.md                    (dashboard_engine row mentions Universe section)
- grep -nE "savings_plan|Universe" docs/CONTEXT_AND_ROADMAP.md
  Pipeline-Phasen-Liste must show savings_plan stage after import and before fundamentals_seed,
  and Dashboard-Phase must mention the Universe section.
- grep -nE "ARCH-P1-001" docs/architecture/05_ARCHITECTURE_BACKLOG.csv
  must be present, status done, title contains "Phase 1 Step 1".

==================================================================
SECTION 11 — Private/Raw Data Check
==================================================================

Verify no private data in committed files:

wc -l data/raw/savings_plan_registry.csv                          (expected: 1)
cat data/raw/savings_plan_registry.csv | head -3                  (expected: header only)

git ls-files data/raw/ | grep -iE "private|real|tr_" || echo OK   (expected: OK)

==================================================================
SECTION 12 — Cross-Reference Findings
==================================================================

Document the cross-reference reality (not what was planned, but what is in HEAD):

- personal_run_engine STAGE_ORDER position of "savings_plan"
- dashboard_engine: how universe is integrated (own function, own output, separate from
  existing KPI/Sections/Summary outputs?)
- dashboard_server: route, JSON endpoint, HTML render method, filter mechanism
- source_as_of_date handling: which records have non-empty dates? how is stale_marker
  derived when date is empty?
- savings_plan_registry CLI defaults: input path, summary path, report path
- platform helpers used (artifact_io, validation, schema_registry) — or local
  schema-order writer for new outputs

==================================================================
OUTPUT FORMAT (Audit Report)
==================================================================

1. Executive verdict
   - ACCEPTED / ACCEPTED_WITH_FINDINGS / REJECTED
   - one-paragraph reason

2. Repo Reality
   - branch, head, status, last commits

3. Commit Sequence
   - 1.1a hash, 1.1b hash, 1.1c hash, with messages

4. Files
   - confirmed new files
   - confirmed changed files
   - unexpected changes (if any)

5. Negative-File Findings
   - per Section 5 check, exact grep outputs

6. Test Distribution
   - total count, sub-counts per relevant test module, reconciliation math

7. Schema-Order Verification
   - sp_summary.csv header
   - dashboard_universe_section.csv header
   - any deviation from expected order

8. Empty-State Behavior
   - exit codes
   - report markers

9. CLI Smoke
   - --help outputs, exit codes
   - verification that "--stage" repeated pattern preserved

10. Docs Consistency
    - per Section 10 grep results

11. Private/Raw Check
    - file sizes, content checks

12. Cross-Reference Findings
    - actual integration as discovered

13. Scope Violations
    - none or itemized

14. Required Fixes Before Phase 1.2
    - none or itemized
    - if any: classification (blocker / nice-to-have)

15. Acceptance Criteria for Phase 1.2 Start
    - clean negative-file verification
    - schema-order preserved
    - no scope violations
    - no broken empty-state behavior
    - tests reproduce as reported

==================================================================
DO NOT
==================================================================

- Do not modify any file in this repository.
- Do not run any command that writes outside /tmp/phase11_review/.
- Do not propose code fixes inside this review; if fixes are needed, only list them.
- Do not start Phase 1.2 scoping in this audit.
- Do not re-audit Patches 1 or 2; they have separate acceptance.