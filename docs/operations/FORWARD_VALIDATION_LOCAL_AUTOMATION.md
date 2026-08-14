# Forward Validation Local Automation

## Boundary

`scripts/run_forward_validation_jobs.ps1` is an optional local wrapper around
two deterministic, idempotent producers:

- `weekly`: refresh `personal_due_trigger_review.csv`
- `quarterly`: refresh the descriptive Forward Validation JSON and Markdown
  report

It does not lock a trigger, confirm a resolution, create an investment
decision, promote a policy, call an LLM, or interact with a broker/order API.
It does not register a Windows Scheduled Task. Enabling or scheduling it remains
an explicit Human Operator action.

## Manual runs

The as-of date is mandatory; the wrapper never substitutes the system date.

```powershell
powershell -NoProfile -File scripts/run_forward_validation_jobs.ps1 -Job weekly -AsOfDate YYYY-MM-DD
powershell -NoProfile -File scripts/run_forward_validation_jobs.ps1 -Job quarterly -AsOfDate YYYY-MM-DD
```

Both jobs overwrite generated, git-ignored outputs from the same processed
inputs. Repeating a command with identical inputs and date produces identical
content and appends no ledger row.

## Optional scheduler setup

If the operator later chooses Windows Task Scheduler, configure it manually to
call one of the commands above with a deliberate date-supply mechanism and a
repo-local working directory. Do not schedule `lock`, `confirm`, `anchor`, any
investment action, or policy change. CIOS v1 intentionally provides no task
registration script, credentials, service account, or GitHub Actions workflow.
