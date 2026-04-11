param(
    [string]$InstanceName = 'oanda_paper_oc',
    [string]$TaskName = 'MT5 Boot Recovery',
    [string]$ConfigPath = (Join-Path $PSScriptRoot '..\config\mt5_instances.json'),
    [int]$DelaySeconds = 90,
    [int]$TimeoutSeconds = 120,
    [switch]$SkipCompile,
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    [pscustomobject]@{
        ok = $true
        removed = $true
        taskName = $TaskName
    } | ConvertTo-Json -Depth 4
    return
}

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$scriptPath = Resolve-Path (Join-Path $PSScriptRoot 'invoke_mt5_boot_recovery.ps1')
$powershellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$currentUser = $env:USERNAME

$arguments = @(
    '-NoProfile'
    '-ExecutionPolicy', 'Bypass'
    '-File', ('"{0}"' -f $scriptPath)
    '-InstanceName', $InstanceName
    '-ConfigPath', ('"{0}"' -f (Resolve-Path $ConfigPath))
    '-DelaySeconds', $DelaySeconds
    '-TimeoutSeconds', $TimeoutSeconds
)
if ($SkipCompile) {
    $arguments += '-SkipCompile'
}
$argumentString = ($arguments -join ' ')

$action = New-ScheduledTaskAction -Execute $powershellExe -Argument $argumentString -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$trigger.Delay = ('PT{0}S' -f $DelaySeconds)
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

$task = Get-ScheduledTask -TaskName $TaskName
[pscustomobject]@{
    ok = $true
    removed = $false
    taskName = $TaskName
    instanceName = $InstanceName
    trigger = 'AtLogOn'
    delaySeconds = $DelaySeconds
    skipCompile = [bool]$SkipCompile
    actionPath = $powershellExe
    actionArguments = $argumentString
    state = [string]$task.State
} | ConvertTo-Json -Depth 6
