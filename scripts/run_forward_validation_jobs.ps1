[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("weekly", "quarterly")]
    [string]$Job,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^\d{4}-\d{2}-\d{2}$")]
    [string]$AsOfDate,

    [string]$PythonExecutable = "python",
    [string]$DecisionJournal = "data/processed/personal_decision_state_capture.csv",
    [string]$TriggerLedger = "data/processed/personal_decision_triggers.csv",
    [string]$ResolutionLedger = "data/processed/personal_trigger_resolutions.csv",
    [string]$DueOutput = "data/processed/personal_due_trigger_review.csv",
    [string]$SummaryOutput = "data/processed/personal_forward_validation_summary.json",
    [string]$ReportOutput = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    if ($Job -eq "weekly") {
        & $PythonExecutable -m src.personal_trigger_resolution scan-due `
            --as-of-date $AsOfDate `
            --trigger-ledger $TriggerLedger `
            --resolution-ledger $ResolutionLedger `
            --output $DueOutput
    }
    else {
        $reportArgs = @(
            "-m", "src.personal_forward_validation", "report",
            "--as-of-date", $AsOfDate,
            "--trigger-ledger", $TriggerLedger,
            "--resolution-ledger", $ResolutionLedger,
            "--decision-journal", $DecisionJournal,
            "--summary-output", $SummaryOutput
        )
        if ($ReportOutput) {
            $reportArgs += @("--report-output", $ReportOutput)
        }
        & $PythonExecutable @reportArgs
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Forward-validation job '$Job' failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
