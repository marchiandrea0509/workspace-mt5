param(
    [string]$InstanceName,
    [string]$ConfigPath = (Join-Path $PSScriptRoot '..\config\mt5_instances.json'),
    [string]$TerminalExe,
    [string]$DataRoot,
    [string]$EaSource
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Resolve-Mt5Instance.ps1')

$resolved = Get-Mt5InstanceConfig -InstanceName $InstanceName -ConfigPath $ConfigPath
if (-not $PSBoundParameters.ContainsKey('TerminalExe')) { $TerminalExe = $resolved.TerminalExe }
if (-not $PSBoundParameters.ContainsKey('DataRoot')) { $DataRoot = $resolved.DataRoot }
if (-not $PSBoundParameters.ContainsKey('EaSource')) { $EaSource = $resolved.EaSource }

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
            if ($text) { return $text }
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
    $lines = $text -split "`r?`n" | Where-Object { $_ -match $Pattern }
    if (-not $lines -or $lines.Count -eq 0) { return $null }
    return $lines[-1]
}

$today = Get-Date -Format 'yyyyMMdd'
$tradeLog = Join-Path $DataRoot ("Logs\$today.log")
$expertLog = Join-Path $DataRoot ("MQL5\Logs\$today.log")
$compileLog = [System.IO.Path]::ChangeExtension($EaSource, '.compile.log')
$trailingDir = Join-Path $DataRoot 'MQL5\Files\gray_bridge\trailing'
$outboxDir = Join-Path $DataRoot 'MQL5\Files\gray_bridge\outbox'
$inboxDir = Join-Path $DataRoot 'MQL5\Files\gray_bridge\inbox'

$running = @(Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $TerminalExe })

$compileText = Get-DecodedText -Path $compileLog
$compileSummary = $null
if ($compileText -match 'Result:[^\r\n]+') {
    $compileSummary = $Matches[0]
}

$result = [pscustomobject]@{
    instanceName = $resolved.Name
    instanceLabel = $resolved.Label
    terminalExe = $TerminalExe
    dataRoot = $DataRoot
    eaSource = $EaSource
    terminalRunning = ($running.Count -gt 0)
    terminalPid = if ($running.Count -gt 0) { $running[0].Id } else { $null }
    terminalStartTime = if ($running.Count -gt 0) { $running[0].StartTime.ToString('s') } else { $null }
    latestCompileResult = $compileSummary
    latestLoadLine = Get-LatestMatchLine -Path $tradeLog -Pattern 'expert GrayPaperBridgeEA .* loaded successfully'
    latestInitLine = Get-LatestMatchLine -Path $expertLog -Pattern 'GrayPaperBridgeEA .* initialized\. Watching gray_bridge\\inbox'
    latestProcessedLine = Get-LatestMatchLine -Path $expertLog -Pattern 'GrayPaperBridgeEA processed ticket '
    trailingConfigCount = if (Test-Path $trailingDir) { @(Get-ChildItem $trailingDir -File).Count } else { 0 }
    inboxCount = if (Test-Path $inboxDir) { @(Get-ChildItem $inboxDir -File).Count } else { 0 }
    outboxCount = if (Test-Path $outboxDir) { @(Get-ChildItem $outboxDir -File).Count } else { 0 }
}

$result | ConvertTo-Json -Depth 4
