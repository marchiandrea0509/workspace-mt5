param(
    [string]$InstanceName,
    [string]$ConfigPath = (Join-Path $PSScriptRoot '..\config\mt5_instances.json'),
    [string]$TerminalExe,
    [string]$MetaEditorExe,
    [string]$DataRoot,
    [string]$Profile,
    [string]$EaSource,
    [string]$LaunchArgs,
    [int]$TimeoutSeconds = 90,
    [switch]$SkipCompile
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Resolve-Mt5Instance.ps1')

$resolved = Get-Mt5InstanceConfig -InstanceName $InstanceName -ConfigPath $ConfigPath
if (-not $PSBoundParameters.ContainsKey('TerminalExe')) { $TerminalExe = $resolved.TerminalExe }
if (-not $PSBoundParameters.ContainsKey('MetaEditorExe')) { $MetaEditorExe = $resolved.MetaEditorExe }
if (-not $PSBoundParameters.ContainsKey('DataRoot')) { $DataRoot = $resolved.DataRoot }
if (-not $PSBoundParameters.ContainsKey('Profile')) { $Profile = $resolved.Profile }
if (-not $PSBoundParameters.ContainsKey('EaSource')) { $EaSource = $resolved.EaSource }
if (-not $PSBoundParameters.ContainsKey('LaunchArgs')) { $LaunchArgs = $resolved.LaunchArgs }

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
        } catch {}
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

function Get-LogLineTimestamp {
    param(
        [string]$Line,
        [datetime]$ReferenceDate
    )
    if (-not $Line) { return $null }
    if ($Line -match "`t(?<time>\d{2}:\d{2}:\d{2}\.\d{3})`t") {
        return [datetime]::ParseExact(
            ('{0} {1}' -f $ReferenceDate.ToString('yyyy-MM-dd'), $Matches.time),
            'yyyy-MM-dd HH:mm:ss.fff',
            [System.Globalization.CultureInfo]::InvariantCulture
        )
    }
    return $null
}

if (-not $SkipCompile) {
    $compileLog = [System.IO.Path]::ChangeExtension($EaSource, '.compile.log')
    & $MetaEditorExe "/compile:$EaSource" "/log:$compileLog" | Out-Null
    $compileText = Get-DecodedText -Path $compileLog
    if ($compileText -notmatch 'Result:\s+0 errors,\s+0 warnings') {
        throw "EA compile failed. See $compileLog"
    }
}

$existing = @(Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $TerminalExe })
if ($existing.Count -gt 0) {
    $existing | Stop-Process -Force
    $stopped = Wait-Until -TimeoutSeconds 20 -Condition {
        -not (Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $TerminalExe })
    }
    if (-not $stopped) {
        throw 'Timed out waiting for MT5 terminal to stop.'
    }
}

$start = Get-Date
$proc = if ($LaunchArgs) {
    Start-Process -FilePath $TerminalExe -ArgumentList $LaunchArgs -PassThru
} else {
    Start-Process -FilePath $TerminalExe -PassThru
}

$running = Wait-Until -TimeoutSeconds 20 -Condition {
    Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
}
if (-not $running) {
    throw 'MT5 terminal did not start successfully.'
}

$tradeLog = Join-Path $DataRoot ("Logs\{0}.log" -f (Get-Date -Format 'yyyyMMdd'))
$expertLog = Join-Path $DataRoot ("MQL5\Logs\{0}.log" -f (Get-Date -Format 'yyyyMMdd'))

$loaded = Wait-Until -TimeoutSeconds $TimeoutSeconds -PollMs 1500 -Condition {
    $line = Get-LatestMatchLine -Path $tradeLog -Pattern 'expert GrayPaperBridgeEA .* loaded successfully'
    $lineTime = Get-LogLineTimestamp -Line $line -ReferenceDate $start
    if (-not $lineTime) { return $false }
    return ($lineTime -ge $start.AddSeconds(-2))
}
if (-not $loaded) {
    throw 'MT5 restarted, but GrayPaperBridgeEA load confirmation was not found in terminal logs.'
}

$initialized = Wait-Until -TimeoutSeconds 10 -PollMs 1500 -Condition {
    $line = Get-LatestMatchLine -Path $expertLog -Pattern 'GrayPaperBridgeEA .* initialized\. Watching gray_bridge\\inbox'
    return [bool]$line
}

$result = [pscustomobject]@{
    ok = $true
    instanceName = $resolved.Name
    instanceLabel = $resolved.Label
    startedAt = $start.ToString('s')
    profile = $Profile
    launchArgs = $LaunchArgs
    pid = $proc.Id
    terminalExe = $TerminalExe
    dataRoot = $DataRoot
    tradeLog = $tradeLog
    expertLog = $expertLog
    latestLoadLine = Get-LatestMatchLine -Path $tradeLog -Pattern 'expert GrayPaperBridgeEA .* loaded successfully'
    latestInitLine = Get-LatestMatchLine -Path $expertLog -Pattern 'GrayPaperBridgeEA .* initialized\. Watching gray_bridge\\inbox'
    initLineObserved = [bool]$initialized
}

$result | ConvertTo-Json -Depth 4
