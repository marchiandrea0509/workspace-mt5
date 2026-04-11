param(
    [string]$InstanceName,
    [string]$ConfigPath = (Join-Path $PSScriptRoot '..\config\mt5_instances.json'),
    [string]$TerminalExe,
    [string]$DataRoot,
    [string]$EaSource,
    [string]$Since
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

$authorizedLine = Get-LatestMatchLine -Path $tradeLog -Pattern "'\d+': authorized on"
$syncLine = Get-LatestMatchLine -Path $tradeLog -Pattern "'\d+': terminal synchronized with"
$loadLine = Get-LatestMatchLine -Path $tradeLog -Pattern 'expert GrayPaperBridgeEA .* loaded successfully'
$initLine = Get-LatestMatchLine -Path $expertLog -Pattern 'GrayPaperBridgeEA .* initialized\. Watching gray_bridge\\inbox'
$processedLine = Get-LatestMatchLine -Path $expertLog -Pattern 'GrayPaperBridgeEA processed ticket '
$terminalRunning = ($running.Count -gt 0)
$sinceTime = $null
if ($Since) {
    $sinceTime = [datetime]::Parse($Since, [System.Globalization.CultureInfo]::InvariantCulture)
}
$referenceDate = Get-Date
$authorizedAt = Get-LogLineTimestamp -Line $authorizedLine -ReferenceDate $referenceDate
$syncAt = Get-LogLineTimestamp -Line $syncLine -ReferenceDate $referenceDate
$loadAt = Get-LogLineTimestamp -Line $loadLine -ReferenceDate $referenceDate
$initAt = Get-LogLineTimestamp -Line $initLine -ReferenceDate $referenceDate
$processedAt = Get-LogLineTimestamp -Line $processedLine -ReferenceDate $referenceDate
$freshAuthorizedObserved = if ($sinceTime) { [bool]($authorizedAt -and $authorizedAt -ge $sinceTime.AddSeconds(-2)) } else { [bool]$authorizedLine }
$freshSynchronizedObserved = if ($sinceTime) { [bool]($syncAt -and $syncAt -ge $sinceTime.AddSeconds(-2)) } else { [bool]$syncLine }
$freshLoadObserved = if ($sinceTime) { [bool]($loadAt -and $loadAt -ge $sinceTime.AddSeconds(-2)) } else { [bool]$loadLine }
$freshInitObserved = if ($sinceTime) { [bool]($initAt -and $initAt -ge $sinceTime.AddSeconds(-2)) } else { [bool]$initLine }

$result = [pscustomobject]@{
    instanceName = $resolved.Name
    instanceLabel = $resolved.Label
    terminalExe = $TerminalExe
    dataRoot = $DataRoot
    eaSource = $EaSource
    terminalRunning = $terminalRunning
    terminalPid = if ($running.Count -gt 0) { $running[0].Id } else { $null }
    terminalStartTime = if ($running.Count -gt 0) { $running[0].StartTime.ToString('s') } else { $null }
    latestCompileResult = $compileSummary
    since = if ($sinceTime) { $sinceTime.ToString('s') } else { $null }
    latestAuthorizedLine = $authorizedLine
    latestSyncLine = $syncLine
    latestLoadLine = $loadLine
    latestInitLine = $initLine
    latestProcessedLine = $processedLine
    latestAuthorizedAt = if ($authorizedAt) { $authorizedAt.ToString('s') } else { $null }
    latestSyncAt = if ($syncAt) { $syncAt.ToString('s') } else { $null }
    latestLoadAt = if ($loadAt) { $loadAt.ToString('s') } else { $null }
    latestInitAt = if ($initAt) { $initAt.ToString('s') } else { $null }
    latestProcessedAt = if ($processedAt) { $processedAt.ToString('s') } else { $null }
    authorizedObserved = [bool]$authorizedLine
    synchronizedObserved = [bool]$syncLine
    loadObserved = [bool]$loadLine
    initObserved = [bool]$initLine
    freshAuthorizedObserved = $freshAuthorizedObserved
    freshSynchronizedObserved = $freshSynchronizedObserved
    freshLoadObserved = $freshLoadObserved
    freshInitObserved = $freshInitObserved
    trailingConfigCount = if (Test-Path $trailingDir) { @(Get-ChildItem $trailingDir -File).Count } else { 0 }
    inboxCount = if (Test-Path $inboxDir) { @(Get-ChildItem $inboxDir -File).Count } else { 0 }
    outboxCount = if (Test-Path $outboxDir) { @(Get-ChildItem $outboxDir -File).Count } else { 0 }
    healthy = ($terminalRunning -and [bool]$authorizedLine -and [bool]$syncLine -and [bool]$loadLine -and [bool]$initLine)
    healthySince = if ($sinceTime) { ($terminalRunning -and $freshAuthorizedObserved -and $freshSynchronizedObserved -and $freshLoadObserved -and $freshInitObserved) } else { $null }
}

$result | ConvertTo-Json -Depth 4
