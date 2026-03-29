param(
    [string]$SourceDir = 'C:\Program Files\OANDA TMS MT5 Terminal',
    [string]$TargetDir = 'C:\MT5_OANDA_PAPER_OC',
    [string]$ShortcutPath = (Join-Path $env:USERPROFILE 'Desktop\MT5 OANDA Paper OC.lnk'),
    [string]$Profile = 'Default',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$eaMirror = Join-Path $workspaceRoot 'mt5_bridge\GrayPaperBridgeEA.mq5'
$pointerPath = Join-Path $workspaceRoot 'mql5\MQL5_OANDA_PAPER_OC'
$readmePath = Join-Path $TargetDir 'OPENCLAW_PORTABLE_INSTANCE.txt'
$terminalExe = Join-Path $TargetDir 'terminal64.exe'
$metaEditorExe = Join-Path $TargetDir 'MetaEditor64.exe'
$mql5Root = Join-Path $TargetDir 'MQL5'
$grayExpertDir = Join-Path $mql5Root 'Experts\Gray'
$bridgeRoot = Join-Path $mql5Root 'Files\gray_bridge'

if (-not (Test-Path (Join-Path $SourceDir 'terminal64.exe'))) {
    throw "Source MT5 install not found or missing terminal64.exe: $SourceDir"
}

if ((Test-Path $TargetDir) -and -not $Force) {
    Write-Host "Target already exists; reusing existing folder: $TargetDir"
} else {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    $null = & robocopy $SourceDir $TargetDir /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path $terminalExe)) {
    throw "Portable target is missing terminal64.exe after copy: $terminalExe"
}

New-Item -ItemType Directory -Path $grayExpertDir -Force | Out-Null
@('inbox','outbox','archive','errors','trailing','trailing_archive') | ForEach-Object {
    New-Item -ItemType Directory -Path (Join-Path $bridgeRoot $_) -Force | Out-Null
}

if (Test-Path $eaMirror) {
    Copy-Item $eaMirror (Join-Path $grayExpertDir 'GrayPaperBridgeEA.mq5') -Force
}

Set-Content -Path $pointerPath -Value (Join-Path $TargetDir 'MQL5') -NoNewline

$readme = @(
    'OpenClaw portable MT5 instance',
    '',
    "Created: $(Get-Date -Format s)",
    "TargetDir: $TargetDir",
    "Launch command: `"$terminalExe`" /portable /profile:$Profile",
    '',
    'Use this instance only for OANDA paper / OpenClaw automation.',
    'After first launch, log into the OANDA paper account, attach GrayPaperBridgeEA to one chart, and enable Algo Trading.'
) -join "`r`n"
Set-Content -Path $readmePath -Value $readme

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $terminalExe
$shortcut.Arguments = "/portable /profile:$Profile"
$shortcut.WorkingDirectory = $TargetDir
$shortcut.IconLocation = $terminalExe
$shortcut.Save()

$result = [pscustomobject]@{
    ok = $true
    sourceDir = $SourceDir
    targetDir = $TargetDir
    terminalExe = $terminalExe
    metaEditorExe = $metaEditorExe
    profile = $Profile
    launchArgs = "/portable /profile:$Profile"
    pointerPath = $pointerPath
    mql5Root = $mql5Root
    eaSeeded = Test-Path (Join-Path $grayExpertDir 'GrayPaperBridgeEA.mq5')
    bridgeRoot = $bridgeRoot
    shortcutPath = $ShortcutPath
    readmePath = $readmePath
}

$result | ConvertTo-Json -Depth 4
