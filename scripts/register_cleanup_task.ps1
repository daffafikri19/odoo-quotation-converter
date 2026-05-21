param(
    [string]$TaskName = "QuotationConverterCleanup",
    [string]$At = "00:00",
    [int]$RetentionDays = 3
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PythonPath = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$CleanupScript = Join-Path $ProjectRoot "scripts\cleanup_old_files.py"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python venv was not found: $PythonPath"
}

if (-not (Test-Path -LiteralPath $CleanupScript)) {
    throw "Cleanup script was not found: $CleanupScript"
}

$actionArgs = "`"$CleanupScript`" --days $RetentionDays"
$action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument $actionArgs `
    -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Delete quotation converter uploads/exports older than $RetentionDays days." `
    -Force

Write-Host "Registered scheduled task '$TaskName' at $At with $RetentionDays-day retention."
