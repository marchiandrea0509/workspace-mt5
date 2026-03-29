$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$defaultConfigPath = Join-Path (Split-Path -Parent $scriptDir) 'config\mt5_instances.json'

function Get-Mt5InstancesConfig {
    param(
        [string]$ConfigPath = $defaultConfigPath
    )

    if (-not (Test-Path $ConfigPath)) {
        throw "MT5 instance config not found: $ConfigPath"
    }

    return Get-Content $ConfigPath -Raw | ConvertFrom-Json
}

function Resolve-Mt5LaunchArgs {
    param(
        [object]$Instance,
        [string]$Profile
    )

    if ($Instance.launchArgs) {
        return [string]$Instance.launchArgs
    }

    $parts = @()
    if ($Instance.portable) {
        $parts += '/portable'
    }
    if ($Profile) {
        $parts += "/profile:$Profile"
    }
    return ($parts -join ' ').Trim()
}

function Get-Mt5InstanceConfig {
    param(
        [string]$InstanceName,
        [string]$ConfigPath = $defaultConfigPath
    )

    $config = Get-Mt5InstancesConfig -ConfigPath $ConfigPath
    $name = if ($InstanceName) { $InstanceName } else { [string]$config.defaultInstance }
    if (-not $name) {
        throw 'No MT5 instance name supplied and no defaultInstance set in config.'
    }

    $prop = $config.instances.PSObject.Properties | Where-Object { $_.Name -eq $name } | Select-Object -First 1
    if (-not $prop) {
        $available = ($config.instances.PSObject.Properties.Name | Sort-Object) -join ', '
        throw "Unknown MT5 instance '$name'. Available: $available"
    }

    $instance = $prop.Value
    $dataRoot = [string]$instance.dataRoot
    $mql5Root = if ($instance.mql5Root) { [string]$instance.mql5Root } else { Join-Path $dataRoot 'MQL5' }
    $bridgeRoot = if ($instance.bridgeRoot) { [string]$instance.bridgeRoot } else { Join-Path $mql5Root 'Files\gray_bridge' }
    $profile = if ($instance.profile) { [string]$instance.profile } else { 'Default' }
    $eaSource = if ($instance.eaSource) { [string]$instance.eaSource } else { Join-Path $mql5Root 'Experts\Gray\GrayPaperBridgeEA.mq5' }

    [pscustomobject]@{
        Name = $name
        Label = [string]$instance.label
        TerminalExe = [string]$instance.terminalExe
        MetaEditorExe = [string]$instance.metaEditorExe
        DataRoot = $dataRoot
        Mql5Root = $mql5Root
        BridgeRoot = $bridgeRoot
        EaSource = $eaSource
        Profile = $profile
        Portable = [bool]$instance.portable
        LaunchArgs = Resolve-Mt5LaunchArgs -Instance $instance -Profile $profile
    }
}
