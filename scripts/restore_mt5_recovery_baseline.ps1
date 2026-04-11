param(
    [string]$InstanceName,
    [string]$ConfigPath = (Join-Path $PSScriptRoot '..\config\mt5_instances.json'),
    [string]$BaselineRoot = (Join-Path $PSScriptRoot '..\state\mt5_recovery_baselines'),
    [string]$SnapshotPath,
    [int]$RestartTimeoutSeconds = 90,
    [switch]$RestartAfterRestore,
    [switch]$SkipCompile,
    [switch]$ForceStopTarget
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Resolve-Mt5Instance.ps1')

function Invoke-BridgeHealth {
    param(
        [string]$InstanceName,
        [string]$ConfigPath,
        [string]$Since
    )

    $params = @{
        InstanceName = $InstanceName
        ConfigPath = $ConfigPath
    }
    if ($Since) {
        $params.Since = $Since
    }

    $raw = & (Join-Path $PSScriptRoot 'check_mt5_bridge_health.ps1') @params 2>&1 | Out-String
    try {
        return ($raw | ConvertFrom-Json -ErrorAction Stop)
    }
    catch {
        throw "Failed to parse bridge health JSON: $raw"
    }
}

function Invoke-BridgeReload {
    param(
        [string]$InstanceName,
        [string]$ConfigPath,
        [int]$TimeoutSeconds,
        [bool]$SkipCompile
    )

    $params = @{
        InstanceName = $InstanceName
        ConfigPath = $ConfigPath
        TimeoutSeconds = $TimeoutSeconds
    }
    if ($SkipCompile) {
        $params.SkipCompile = $true
    }

    $raw = & (Join-Path $PSScriptRoot 'reload_mt5_bridge.ps1') @params 2>&1 | Out-String
    try {
        return ($raw | ConvertFrom-Json -ErrorAction Stop)
    }
    catch {
        throw "Failed to parse reload JSON: $raw"
    }
}

function Get-TargetProcesses {
    param([string]$TerminalExe)

    return @(
        Get-Process terminal64 -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -eq $TerminalExe } |
            Sort-Object StartTime -Descending
    )
}

function Copy-DirectorySafe {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) { return $false }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Copy-Item -Path $Source -Destination $Destination -Recurse -Force
    return $true
}

function Replace-DirectoryFromSnapshot {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        throw "Snapshot directory missing: $Source"
    }

    if (Test-Path $Destination) {
        Remove-Item -Path $Destination -Recurse -Force
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Copy-Item -Path $Source -Destination $Destination -Recurse -Force
}

$resolved = Get-Mt5InstanceConfig -InstanceName $InstanceName -ConfigPath $ConfigPath
$instanceDir = Join-Path $BaselineRoot $resolved.Name
$latestPointerPath = Join-Path $instanceDir 'LATEST.json'

if (-not $SnapshotPath) {
    if (-not (Test-Path $latestPointerPath)) {
        throw "No latest baseline pointer found: $latestPointerPath"
    }
    $latest = Get-Content $latestPointerPath -Raw | ConvertFrom-Json
    $SnapshotPath = [string]$latest.latestSnapshot
}

if (-not (Test-Path $SnapshotPath)) {
    throw "Snapshot path not found: $SnapshotPath"
}

$targetProcesses = Get-TargetProcesses -TerminalExe $resolved.TerminalExe
if ($targetProcesses.Count -gt 0) {
    if ($ForceStopTarget) {
        $targetProcesses | Stop-Process -Force -ErrorAction Stop
        Start-Sleep -Seconds 2
    }
    else {
        throw 'Target MT5 process is still running. Stop it first or rerun with -ForceStopTarget.'
    }
}

$restoreStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$safetyBackupDir = Join-Path $instanceDir ("pre_restore_backup_$restoreStamp")
$configBackupDir = Join-Path $safetyBackupDir 'Config'
$mqlProfilesBackupDir = Join-Path $safetyBackupDir 'MQL5\Profiles'
New-Item -ItemType Directory -Force -Path $configBackupDir | Out-Null

$configFiles = @('terminal.ini', 'settings.ini', 'common.ini')
$backedUpConfigFiles = @()
foreach ($name in $configFiles) {
    $source = Join-Path $resolved.DataRoot (Join-Path 'Config' $name)
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination (Join-Path $configBackupDir $name) -Force
        $backedUpConfigFiles += $name
    }
}
$backupProfilesCopied = Copy-DirectorySafe -Source (Join-Path $resolved.DataRoot 'MQL5\Profiles') -Destination $mqlProfilesBackupDir

$snapshotConfigDir = Join-Path $SnapshotPath 'Config'
$snapshotProfilesDir = Join-Path $SnapshotPath 'MQL5\Profiles'
if (-not (Test-Path $snapshotProfilesDir)) {
    throw "Snapshot does not contain MQL5 profile data: $snapshotProfilesDir"
}

foreach ($name in $configFiles) {
    $source = Join-Path $snapshotConfigDir $name
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination (Join-Path $resolved.DataRoot (Join-Path 'Config' $name)) -Force
    }
}

Replace-DirectoryFromSnapshot -Source $snapshotProfilesDir -Destination (Join-Path $resolved.DataRoot 'MQL5\Profiles')

$restartResult = $null
$healthAfterRestart = $null
if ($RestartAfterRestore) {
    $restartResult = Invoke-BridgeReload -InstanceName $resolved.Name -ConfigPath $ConfigPath -TimeoutSeconds $RestartTimeoutSeconds -SkipCompile:$SkipCompile.IsPresent
    $healthAfterRestart = Invoke-BridgeHealth -InstanceName $resolved.Name -ConfigPath $ConfigPath -Since $restartResult.startedAt
}

$result = [pscustomobject]@{
    ok = $true
    instanceName = $resolved.Name
    restoredFromSnapshot = $SnapshotPath
    safetyBackupDir = $safetyBackupDir
    backedUpConfigFiles = @($backedUpConfigFiles)
    backupProfilesCopied = $backupProfilesCopied
    restartPerformed = [bool]$RestartAfterRestore
    restartResult = $restartResult
    healthAfterRestart = $healthAfterRestart
}

$result | ConvertTo-Json -Depth 8
