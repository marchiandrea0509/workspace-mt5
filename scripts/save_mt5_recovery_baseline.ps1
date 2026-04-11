param(
    [string]$InstanceName,
    [string]$ConfigPath = (Join-Path $PSScriptRoot '..\config\mt5_instances.json'),
    [string]$BaselineRoot = (Join-Path $PSScriptRoot '..\state\mt5_recovery_baselines'),
    [int]$CloseTimeoutSeconds = 45,
    [int]$RestartTimeoutSeconds = 90,
    [switch]$SkipCompile,
    [switch]$ForceCloseOnTimeout,
    [switch]$NoRestart
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Resolve-Mt5Instance.ps1')

function Invoke-BridgeHealth {
    param(
        [string]$InstanceName,
        [string]$ConfigPath
    )

    $raw = & (Join-Path $PSScriptRoot 'check_mt5_bridge_health.ps1') -InstanceName $InstanceName -ConfigPath $ConfigPath 2>&1 | Out-String
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

function Wait-Until {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds = 30,
        [int]$PollMs = 1000
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) { return $true }
        Start-Sleep -Milliseconds $PollMs
    }
    return $false
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

$resolved = Get-Mt5InstanceConfig -InstanceName $InstanceName -ConfigPath $ConfigPath
$instanceDir = Join-Path $BaselineRoot $resolved.Name
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$snapshotDir = Join-Path $instanceDir $timestamp
$configSnapshotDir = Join-Path $snapshotDir 'Config'
$mqlProfilesSnapshotDir = Join-Path $snapshotDir 'MQL5\Profiles'
$metaDir = Join-Path $snapshotDir '_meta'
$latestPointerPath = Join-Path $instanceDir 'LATEST.json'

$healthBefore = Invoke-BridgeHealth -InstanceName $resolved.Name -ConfigPath $ConfigPath
if (-not $healthBefore.healthy) {
    throw 'Refusing to save a recovery baseline while the portable MT5 bridge is not healthy.'
}

$targetProcesses = Get-TargetProcesses -TerminalExe $resolved.TerminalExe
if ($targetProcesses.Count -eq 0) {
    throw 'No target MT5 process found for baseline save.'
}
if ($targetProcesses.Count -gt 1) {
    throw 'More than one target MT5 process is running. Clean up duplicates before saving a baseline.'
}

$proc = $targetProcesses[0]
$closeAttempted = $false
$closedGracefully = $false
$forceClosed = $false
$closeWarnings = @()

if ($proc.MainWindowHandle -ne 0) {
    $closeAttempted = $true
    [void]$proc.CloseMainWindow()
    $closedGracefully = Wait-Until -TimeoutSeconds $CloseTimeoutSeconds -Condition {
        -not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)
    }
}
else {
    $closeWarnings += 'Target process did not expose a main window handle; graceful close was not possible.'
}

if (-not $closedGracefully) {
    if ($ForceCloseOnTimeout) {
        Stop-Process -Id $proc.Id -Force -ErrorAction Stop
        $forceClosed = $true
        Wait-Until -TimeoutSeconds 15 -Condition {
            -not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)
        } | Out-Null
        $closeWarnings += 'Target MT5 process required force close; on-disk profile flush may still be incomplete.'
    }
    else {
        throw 'Timed out waiting for MT5 to close gracefully. Re-run with -ForceCloseOnTimeout only if you explicitly want a weaker baseline capture.'
    }
}

New-Item -ItemType Directory -Force -Path $configSnapshotDir | Out-Null
New-Item -ItemType Directory -Force -Path $metaDir | Out-Null

$configFiles = @('terminal.ini', 'settings.ini', 'common.ini')
$copiedConfigFiles = @()
foreach ($name in $configFiles) {
    $source = Join-Path $resolved.DataRoot (Join-Path 'Config' $name)
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination (Join-Path $configSnapshotDir $name) -Force
        $copiedConfigFiles += $name
    }
}

$mqlProfilesSource = Join-Path $resolved.DataRoot 'MQL5\Profiles'
$profilesCopied = Copy-DirectorySafe -Source $mqlProfilesSource -Destination $mqlProfilesSnapshotDir
if (-not $profilesCopied) {
    throw "MQL5 profile source missing: $mqlProfilesSource"
}

$chart03 = Join-Path $mqlProfilesSource 'Charts\Default\chart03.chr'
$chart03Info = if (Test-Path $chart03) {
    $item = Get-Item $chart03
    [pscustomobject]@{
        path = $chart03
        lastWriteTime = $item.LastWriteTime.ToString('s')
        length = $item.Length
    }
} else { $null }

$manifest = [pscustomobject]@{
    savedAt = (Get-Date).ToString('s')
    instanceName = $resolved.Name
    instanceLabel = $resolved.Label
    terminalExe = $resolved.TerminalExe
    dataRoot = $resolved.DataRoot
    profile = $resolved.Profile
    launchArgs = $resolved.LaunchArgs
    snapshotDir = $snapshotDir
    copiedConfigFiles = @($copiedConfigFiles)
    copiedMqlProfiles = $profilesCopied
    sourceOfTruth = @(
        'Config\\terminal.ini',
        'Config\\settings.ini',
        'Config\\common.ini',
        'MQL5\\Profiles\\**'
    )
    note = 'Top-level portable Profiles\\... tree is intentionally not treated as authoritative recovery input because it appears stale versus MQL5\\Profiles on this installation.'
    healthBeforeSave = $healthBefore
    chart03Info = $chart03Info
    closeAttempted = $closeAttempted
    closedGracefully = $closedGracefully
    forceClosed = $forceClosed
    warnings = @($closeWarnings)
}

$manifest | ConvertTo-Json -Depth 8 | Set-Content -Path (Join-Path $metaDir 'manifest.json') -Encoding UTF8
@{
    instanceName = $resolved.Name
    latestSnapshot = $snapshotDir
    savedAt = (Get-Date).ToString('s')
} | ConvertTo-Json -Depth 4 | Set-Content -Path $latestPointerPath -Encoding UTF8

$restartResult = $null
$healthAfterRestart = $null
if (-not $NoRestart) {
    $restartResult = Invoke-BridgeReload -InstanceName $resolved.Name -ConfigPath $ConfigPath -TimeoutSeconds $RestartTimeoutSeconds -SkipCompile:$SkipCompile.IsPresent
    $healthAfterRestart = Invoke-BridgeHealth -InstanceName $resolved.Name -ConfigPath $ConfigPath
}

$result = [pscustomobject]@{
    ok = $true
    instanceName = $resolved.Name
    snapshotDir = $snapshotDir
    latestPointerPath = $latestPointerPath
    closedGracefully = $closedGracefully
    forceClosed = $forceClosed
    warnings = @($closeWarnings)
    healthBeforeSave = $healthBefore
    restartPerformed = (-not $NoRestart)
    restartResult = $restartResult
    healthAfterRestart = $healthAfterRestart
}

$result | ConvertTo-Json -Depth 8
