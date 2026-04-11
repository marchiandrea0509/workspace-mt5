param(
    [string]$InstanceName,
    [string]$ConfigPath = (Join-Path $PSScriptRoot '..\config\mt5_instances.json'),
    [string]$BaselineRoot = (Join-Path $PSScriptRoot '..\state\mt5_recovery_baselines'),
    [string]$LogRoot = (Join-Path $PSScriptRoot '..\state\mt5_boot_recovery_logs'),
    [int]$DelaySeconds = 90,
    [int]$TimeoutSeconds = 120,
    [switch]$SkipCompile
)

$ErrorActionPreference = 'Stop'

function Write-RunLog {
    param(
        [string]$Path,
        [string]$Message
    )

    $line = '[{0}] {1}' -f (Get-Date).ToString('s'), $Message
    Add-Content -Path $Path -Value $line -Encoding UTF8
}

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logPath = Join-Path $LogRoot ("mt5_boot_recovery_$stamp.log")

Write-RunLog -Path $logPath -Message "Boot recovery starting for instance '$InstanceName'. DelaySeconds=$DelaySeconds TimeoutSeconds=$TimeoutSeconds SkipCompile=$($SkipCompile.IsPresent)"

if ($DelaySeconds -gt 0) {
    Write-RunLog -Path $logPath -Message "Sleeping for $DelaySeconds seconds to let the user session and network settle."
    Start-Sleep -Seconds $DelaySeconds
}

$params = @{
    InstanceName = $InstanceName
    ConfigPath = $ConfigPath
    BaselineRoot = $BaselineRoot
    TimeoutSeconds = $TimeoutSeconds
    TryRestoreBaselineOnMissingEa = $true
}
if ($SkipCompile) {
    $params.SkipCompile = $true
}

$raw = & (Join-Path $PSScriptRoot 'recover_mt5_after_shutdown.ps1') @params 2>&1 | Out-String
Write-RunLog -Path $logPath -Message 'Recovery script completed. Raw JSON/result follows.'
Add-Content -Path $logPath -Value $raw -Encoding UTF8

try {
    $result = $raw | ConvertFrom-Json -ErrorAction Stop
}
catch {
    Write-RunLog -Path $logPath -Message "Failed to parse recovery JSON: $($_.Exception.Message)"
    throw
}

$outcome = [string]$result.outcome
$healthySince = $null
if ($result.finalHealth -and $null -ne $result.finalHealth.healthySince) {
    $healthySince = [bool]$result.finalHealth.healthySince
}
$healthy = if ($result.finalHealth) { [bool]$result.finalHealth.healthy } else { $false }

Write-RunLog -Path $logPath -Message "Outcome=$outcome healthy=$healthy healthySince=$healthySince"

if ($outcome -ne 'RECOVERED_FULLY' -or ($null -ne $healthySince -and -not $healthySince)) {
    throw "Boot recovery finished in non-ideal state. Outcome=$outcome healthy=$healthy healthySince=$healthySince"
}

Write-RunLog -Path $logPath -Message 'Boot recovery completed successfully.'
