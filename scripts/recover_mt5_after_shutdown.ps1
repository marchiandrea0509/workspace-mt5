param(
    [string]$InstanceName,
    [string]$ConfigPath = (Join-Path $PSScriptRoot '..\config\mt5_instances.json'),
    [string]$PointerPath = (Join-Path $PSScriptRoot '..\mql5\MQL5'),
    [string]$BaselineRoot = (Join-Path $PSScriptRoot '..\state\mt5_recovery_baselines'),
    [int]$TimeoutSeconds = 90,
    [switch]$SkipCompile,
    [switch]$NoCleanup,
    [switch]$TryRestoreBaselineOnMissingEa
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Resolve-Mt5Instance.ps1')

function Get-DecodedText {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return '' }

    $stream = $null
    try {
        $stream = New-Object System.IO.FileStream($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        $buffer = New-Object byte[] $stream.Length
        [void]$stream.Read($buffer, 0, $buffer.Length)
    }
    finally {
        if ($stream) { $stream.Dispose() }
    }

    foreach ($encoding in @([System.Text.Encoding]::Unicode, [System.Text.Encoding]::UTF8, [System.Text.Encoding]::ASCII)) {
        try {
            $text = $encoding.GetString($buffer)
            $clean = $text -replace "`0", ''
            if ($clean) { return $clean }
        }
        catch {}
    }

    return ''
}

function Get-LatestMatchLine {
    param(
        [string]$Path,
        [string]$Pattern
    )

    $text = Get-DecodedText -Path $Path
    if (-not $text) { return $null }

    $lines = @($text -split "`r?`n" | Where-Object { $_ -match $Pattern })
    if (-not $lines -or $lines.Count -eq 0) { return $null }
    return $lines[-1]
}

function Normalize-PathString {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
    try {
        return ([System.IO.Path]::GetFullPath($Path)).Trim().TrimEnd('\\')
    }
    catch {
        return $Path.Trim().TrimEnd('\\')
    }
}

function Get-PointerInfo {
    param(
        [string]$PointerPath,
        [string]$ExpectedMql5Root
    )

    $exists = Test-Path $PointerPath
    $raw = if ($exists) { (Get-Content $PointerPath -Raw).Trim() } else { $null }
    $normalizedRaw = Normalize-PathString -Path $raw
    $normalizedExpected = Normalize-PathString -Path $ExpectedMql5Root

    [pscustomobject]@{
        path = $PointerPath
        exists = $exists
        raw = $raw
        normalizedRaw = $normalizedRaw
        expected = $ExpectedMql5Root
        normalizedExpected = $normalizedExpected
        matchesExpected = ($exists -and $normalizedRaw -eq $normalizedExpected)
    }
}

function Get-CompileSummary {
    param([string]$CompileLog)
    $compileText = Get-DecodedText -Path $CompileLog
    if ($compileText -match 'Result:[^\r\n]+') {
        return $Matches[0]
    }
    return $null
}

function Get-BridgeHealth {
    param([object]$Resolved)

    $today = Get-Date -Format 'yyyyMMdd'
    $tradeLog = Join-Path $Resolved.DataRoot ("Logs\$today.log")
    $expertLog = Join-Path $Resolved.DataRoot ("MQL5\Logs\$today.log")
    $compileLog = [System.IO.Path]::ChangeExtension($Resolved.EaSource, '.compile.log')
    $trailingDir = Join-Path $Resolved.BridgeRoot 'trailing'
    $outboxDir = Join-Path $Resolved.BridgeRoot 'outbox'
    $inboxDir = Join-Path $Resolved.BridgeRoot 'inbox'

    $running = @(
        Get-Process terminal64 -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -eq $Resolved.TerminalExe } |
            Sort-Object StartTime -Descending
    )

    $loadLine = Get-LatestMatchLine -Path $tradeLog -Pattern 'expert GrayPaperBridgeEA .* loaded successfully'
    $initLine = Get-LatestMatchLine -Path $expertLog -Pattern 'GrayPaperBridgeEA .* initialized\. Watching gray_bridge\\inbox'
    $processedLine = Get-LatestMatchLine -Path $expertLog -Pattern 'GrayPaperBridgeEA processed ticket '
    $authLine = Get-LatestMatchLine -Path $tradeLog -Pattern "'\d+': authorized on"
    $syncLine = Get-LatestMatchLine -Path $tradeLog -Pattern "'\d+': terminal synchronized with"

    [pscustomobject]@{
        instanceName = $Resolved.Name
        instanceLabel = $Resolved.Label
        terminalExe = $Resolved.TerminalExe
        dataRoot = $Resolved.DataRoot
        mql5Root = $Resolved.Mql5Root
        bridgeRoot = $Resolved.BridgeRoot
        eaSource = $Resolved.EaSource
        tradeLog = $tradeLog
        expertLog = $expertLog
        terminalRunning = ($running.Count -gt 0)
        runningPidCount = $running.Count
        targetPids = @($running | ForEach-Object { $_.Id })
        terminalPid = if ($running.Count -gt 0) { $running[0].Id } else { $null }
        terminalStartTime = if ($running.Count -gt 0) { $running[0].StartTime.ToString('s') } else { $null }
        latestCompileResult = Get-CompileSummary -CompileLog $compileLog
        latestAuthorizedLine = $authLine
        latestSyncLine = $syncLine
        latestLoadLine = $loadLine
        latestInitLine = $initLine
        latestProcessedLine = $processedLine
        authorizedObserved = [bool]$authLine
        synchronizedObserved = [bool]$syncLine
        loadObserved = [bool]$loadLine
        initObserved = [bool]$initLine
        trailingConfigCount = if (Test-Path $trailingDir) { @(Get-ChildItem $trailingDir -File).Count } else { 0 }
        inboxCount = if (Test-Path $inboxDir) { @(Get-ChildItem $inboxDir -File).Count } else { 0 }
        outboxCount = if (Test-Path $outboxDir) { @(Get-ChildItem $outboxDir -File).Count } else { 0 }
        healthy = (($running.Count -gt 0) -and [bool]$authLine -and [bool]$syncLine -and [bool]$loadLine -and [bool]$initLine)
    }
}

function Get-ProcessInventory {
    param(
        [object]$Resolved,
        [object]$Config
    )

    $targetExe = Normalize-PathString -Path $Resolved.TerminalExe
    $instances = @($Config.instances.PSObject.Properties)

    $processes = @(Get-CimInstance Win32_Process -Filter "name='terminal64.exe'" | Sort-Object CreationDate)
    $rows = foreach ($proc in $processes) {
        $exe = Normalize-PathString -Path $proc.ExecutablePath
        $matchedInstance = $null
        foreach ($instanceProp in $instances) {
            $instanceExe = Normalize-PathString -Path ([string]$instanceProp.Value.terminalExe)
            if ($instanceExe -and $exe -and $instanceExe -eq $exe) {
                $matchedInstance = $instanceProp.Name
                break
            }
        }

        $created = $null
        try {
            $created = [System.Management.ManagementDateTimeConverter]::ToDateTime($proc.CreationDate).ToString('s')
        }
        catch {
            $created = [string]$proc.CreationDate
        }

        $classification = if ($exe -and $exe -eq $targetExe) {
            'target'
        }
        elseif ($matchedInstance) {
            'fallback'
        }
        else {
            'unknown'
        }

        [pscustomobject]@{
            pid = [int]$proc.ProcessId
            executablePath = $proc.ExecutablePath
            commandLine = $proc.CommandLine
            createdAt = $created
            instanceName = $matchedInstance
            classification = $classification
            isTarget = ($classification -eq 'target')
        }
    }

    return @($rows)
}

function Stop-Mt5Processes {
    param(
        [int[]]$Pids,
        [string]$Reason
    )

    $closed = @()
    $errors = @()
    foreach ($pid in @($Pids | Where-Object { $_ })) {
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            $closed += $pid
        }
        catch {
            $errors += [pscustomobject]@{
                pid = $pid
                reason = $Reason
                error = $_.Exception.Message
            }
        }
    }

    if ($closed.Count -gt 0) {
        Start-Sleep -Seconds 2
    }

    [pscustomobject]@{
        closed = @($closed)
        errors = @($errors)
    }
}

function Invoke-BridgeReload {
    param(
        [object]$Resolved,
        [string]$ConfigPath,
        [int]$TimeoutSeconds,
        [bool]$SkipCompile
    )

    $params = @{
        InstanceName = $Resolved.Name
        ConfigPath = $ConfigPath
        TimeoutSeconds = $TimeoutSeconds
    }
    if ($SkipCompile) {
        $params.SkipCompile = $true
    }

    $raw = & (Join-Path $PSScriptRoot 'reload_mt5_bridge.ps1') @params 2>&1 | Out-String
    $json = $null
    try {
        $json = $raw | ConvertFrom-Json -ErrorAction Stop
    }
    catch {}

    [pscustomobject]@{
        raw = $raw.Trim()
        json = $json
    }
}

function Get-LatestBaselineInfo {
    param(
        [string]$BaselineRoot,
        [string]$InstanceName
    )

    $pointerPath = Join-Path (Join-Path $BaselineRoot $InstanceName) 'LATEST.json'
    if (-not (Test-Path $pointerPath)) {
        return [pscustomobject]@{
            available = $false
            pointerPath = $pointerPath
            latestSnapshot = $null
        }
    }

    $payload = Get-Content $pointerPath -Raw | ConvertFrom-Json
    [pscustomobject]@{
        available = [bool]$payload.latestSnapshot
        pointerPath = $pointerPath
        latestSnapshot = [string]$payload.latestSnapshot
        savedAt = [string]$payload.savedAt
    }
}

function Invoke-BaselineRestore {
    param(
        [object]$Resolved,
        [string]$ConfigPath,
        [string]$BaselineRoot,
        [int]$TimeoutSeconds,
        [bool]$SkipCompile
    )

    $params = @{
        InstanceName = $Resolved.Name
        ConfigPath = $ConfigPath
        BaselineRoot = $BaselineRoot
        RestartAfterRestore = $true
        ForceStopTarget = $true
        RestartTimeoutSeconds = $TimeoutSeconds
    }
    if ($SkipCompile) {
        $params.SkipCompile = $true
    }

    $raw = & (Join-Path $PSScriptRoot 'restore_mt5_recovery_baseline.ps1') @params 2>&1 | Out-String
    $json = $null
    try {
        $json = $raw | ConvertFrom-Json -ErrorAction Stop
    }
    catch {}

    [pscustomobject]@{
        raw = $raw.Trim()
        json = $json
    }
}

$config = Get-Mt5InstancesConfig -ConfigPath $ConfigPath
$resolved = Get-Mt5InstanceConfig -InstanceName $InstanceName -ConfigPath $ConfigPath
$pointer = Get-PointerInfo -PointerPath $PointerPath -ExpectedMql5Root $resolved.Mql5Root
$baseline = Get-LatestBaselineInfo -BaselineRoot $BaselineRoot -InstanceName $resolved.Name
$beforeInventory = Get-ProcessInventory -Resolved $resolved -Config $config
$initialHealth = Get-BridgeHealth -Resolved $resolved

$actions = [ordered]@{
    restartAttempted = $false
    restartSucceeded = $false
    restartError = $null
    restartDetails = $null
    baselineAvailable = [bool]$baseline.available
    baselinePointerPath = $baseline.pointerPath
    baselineSnapshotPath = $baseline.latestSnapshot
    baselineRestoreAttempted = $false
    baselineRestoreSucceeded = $false
    baselineRestoreError = $null
    baselineRestoreDetails = $null
    cleanupAttempted = $false
    cleanupSkippedReason = $null
    closedFallbackPids = @()
    closedDuplicateTargetPids = @()
    cleanupErrors = @()
    keptTargetPid = $null
}

$healthAfterRestart = $initialHealth
if (-not $initialHealth.terminalRunning) {
    $actions.restartAttempted = $true
    try {
        $reload = Invoke-BridgeReload -Resolved $resolved -ConfigPath $ConfigPath -TimeoutSeconds $TimeoutSeconds -SkipCompile:$SkipCompile.IsPresent
        $actions.restartSucceeded = $true
        $actions.restartDetails = if ($reload.json) { $reload.json } else { $reload.raw }
    }
    catch {
        $actions.restartError = $_.Exception.Message
    }

    $healthAfterRestart = Get-BridgeHealth -Resolved $resolved
}

$healthBeforeCleanup = $healthAfterRestart
if ($TryRestoreBaselineOnMissingEa -and -not $healthBeforeCleanup.healthy -and $baseline.available) {
    $actions.baselineRestoreAttempted = $true
    try {
        $restore = Invoke-BaselineRestore -Resolved $resolved -ConfigPath $ConfigPath -BaselineRoot $BaselineRoot -TimeoutSeconds $TimeoutSeconds -SkipCompile:$SkipCompile.IsPresent
        $actions.baselineRestoreSucceeded = $true
        $actions.baselineRestoreDetails = if ($restore.json) { $restore.json } else { $restore.raw }
    }
    catch {
        $actions.baselineRestoreError = $_.Exception.Message
    }

    $healthBeforeCleanup = Get-BridgeHealth -Resolved $resolved
}

if ($NoCleanup) {
    $actions.cleanupSkippedReason = 'NoCleanup switch supplied.'
}
elseif (-not $healthBeforeCleanup.healthy) {
    $actions.cleanupSkippedReason = 'Portable target is not fully healthy; cleanup withheld by guardrail.'
}
else {
    $actions.cleanupAttempted = $true

    $midInventory = Get-ProcessInventory -Resolved $resolved -Config $config
    $fallbackPids = @($midInventory | Where-Object { $_.classification -eq 'fallback' } | ForEach-Object { $_.pid })
    if ($fallbackPids.Count -gt 0) {
        $fallbackStop = Stop-Mt5Processes -Pids $fallbackPids -Reason 'fallback'
        $actions.closedFallbackPids = @($fallbackStop.closed)
        $actions.cleanupErrors += @($fallbackStop.errors)
    }

    $postFallbackInventory = Get-ProcessInventory -Resolved $resolved -Config $config
    $targetProcesses = @($postFallbackInventory | Where-Object { $_.isTarget } | Sort-Object createdAt -Descending)
    if ($targetProcesses.Count -gt 0) {
        $actions.keptTargetPid = $targetProcesses[0].pid
    }
    if ($targetProcesses.Count -gt 1) {
        $duplicatePids = @($targetProcesses | Select-Object -Skip 1 | ForEach-Object { $_.pid })
        $duplicateStop = Stop-Mt5Processes -Pids $duplicatePids -Reason 'duplicate-target'
        $actions.closedDuplicateTargetPids = @($duplicateStop.closed)
        $actions.cleanupErrors += @($duplicateStop.errors)
    }
}

$afterInventory = Get-ProcessInventory -Resolved $resolved -Config $config
$finalHealth = Get-BridgeHealth -Resolved $resolved
$finalTargetCount = @($afterInventory | Where-Object { $_.isTarget }).Count
$finalFallbackCount = @($afterInventory | Where-Object { $_.classification -eq 'fallback' }).Count

$outcome = if (
    $finalHealth.healthy -and
    $finalTargetCount -eq 1 -and
    $finalFallbackCount -eq 0
) {
    'RECOVERED_FULLY'
}
elseif (
    $finalHealth.terminalRunning -and
    $finalHealth.authorizedObserved -and
    $finalHealth.synchronizedObserved -and
    (-not ($finalHealth.loadObserved -and $finalHealth.initObserved))
) {
    'RECOVERED_PARTIAL_MANUAL_EA_ATTACH_REQUIRED'
}
elseif (
    ($finalTargetCount -gt 1) -or ($finalFallbackCount -gt 0)
) {
    'FAILED_AMBIGUOUS_DUPLICATE_STATE'
}
elseif (-not $finalHealth.terminalRunning) {
    'FAILED_PORTABLE_START'
}
elseif (
    $finalHealth.terminalRunning -and
    (-not $finalHealth.authorizedObserved -or -not $finalHealth.synchronizedObserved)
) {
    'FAILED_AUTH_OR_SYNC'
}
else {
    'FAILED_AMBIGUOUS_DUPLICATE_STATE'
}

$warnings = @()
if (-not $pointer.exists) {
    $warnings += "Workspace pointer missing: $($pointer.path)"
}
elseif (-not $pointer.matchesExpected) {
    $warnings += "Workspace pointer mismatch: '$($pointer.raw)' (expected '$($pointer.expected)')"
}
if ($actions.restartError) {
    $warnings += "Restart attempt error: $($actions.restartError)"
}
if ($actions.baselineRestoreError) {
    $warnings += "Baseline restore error: $($actions.baselineRestoreError)"
}
if ($actions.cleanupErrors.Count -gt 0) {
    $warnings += 'One or more cleanup actions failed; inspect cleanupErrors.'
}

$recommendedNextStep = switch ($outcome) {
    'RECOVERED_FULLY' { 'No immediate action required. Keep only the portable MT5 terminal running and continue monitoring normally.' }
    'RECOVERED_PARTIAL_MANUAL_EA_ATTACH_REQUIRED' {
        if ($baseline.available) {
            'Portable MT5 is up but the EA/profile state is incomplete. Try the baseline-aware recovery path: powershell -ExecutionPolicy Bypass -File scripts\recover_mt5_after_shutdown.ps1 -InstanceName oanda_paper_oc -TryRestoreBaselineOnMissingEa. If that still fails, confirm File -> Open Data Folder points to C:\MT5_OANDA_PAPER_OC, attach GrayPaperBridgeEA to a chart, enable Algo Trading, then rerun the health check.'
        }
        else {
            'Open the portable MT5 terminal, confirm File -> Open Data Folder points to C:\MT5_OANDA_PAPER_OC, attach GrayPaperBridgeEA to a chart, enable Algo Trading, then rerun this recovery script or the bridge health check.'
        }
    }
    'FAILED_PORTABLE_START' { 'Investigate why the portable MT5 terminal did not stay running. Check terminal launch permissions, terminal logs, and whether another MT5 process is conflicting.' }
    'FAILED_AUTH_OR_SYNC' { 'Portable MT5 started but broker authorization/synchronization was not confirmed. Inspect the portable terminal Journal and network/login state before attempting cleanup.' }
    default { 'Review MT5 process inventory and logs manually. Resolve duplicate/fallback terminals carefully, keeping the portable instance as the intended automation target.' }
}

$result = [pscustomobject]@{
    ranAt = (Get-Date).ToString('s')
    instanceName = $resolved.Name
    instanceLabel = $resolved.Label
    pointer = $pointer
    baseline = $baseline
    outcome = $outcome
    recommendedNextStep = $recommendedNextStep
    warnings = @($warnings)
    beforeInventory = @($beforeInventory)
    initialHealth = $initialHealth
    actions = [pscustomobject]$actions
    healthBeforeCleanup = $healthBeforeCleanup
    afterInventory = @($afterInventory)
    finalHealth = $finalHealth
}

$result | ConvertTo-Json -Depth 8
