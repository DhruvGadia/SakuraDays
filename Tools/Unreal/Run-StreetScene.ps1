param(
    [ValidateSet('plan', 'validate', 'import', 'assemble', 'test')]
    [string]$Mode = 'validate',
    [string]$Revision = '',
    [string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8'
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$Project = Join-Path $ProjectRoot 'sakuradays.uproject'
if (!(Test-Path -LiteralPath $Project -PathType Leaf)) {
    throw "SakuraDays project not found: $Project"
}
if ($Revision -and $Revision -notmatch '^[A-Za-z0-9_]{1,32}$') {
    throw 'Revision must contain 1-32 letters, numbers or underscores.'
}
if ($Revision -and $Mode -in @('assemble', 'test')) {
    throw 'Revision selects imported packages only. Run import with that revision before assemble/test.'
}
$Running = @(Get-Process -Name UnrealEditor, UnrealEditor-Cmd -ErrorAction SilentlyContinue)
if ($Running.Count -gt 0) {
    throw 'An Unreal Editor or editor commandlet is already running. Close it normally or wait for it to finish before launching a separate street workflow process. Save any unsaved work first.'
}
$oldMode = $env:SAKURA_STREET_IMPORT_MODE
$oldRevision = $env:SAKURA_STREET_IMPORT_REVISION
try {
    $env:SAKURA_STREET_IMPORT_MODE = if ($Mode -in @('plan', 'validate', 'import')) { $Mode } else { 'validate' }
    $env:SAKURA_STREET_IMPORT_REVISION = $Revision
    if ($Mode -eq 'test') {
        $Editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
        $Script = (Join-Path $PSScriptRoot 'test_street_scene.py').Replace('\', '/')
        if (!(Test-Path -LiteralPath $Editor -PathType Leaf)) { throw "Editor not found: $Editor" }
        Write-Output 'Launching the full editor for genuine PIE navigation and two-camera capture.'
        Write-Output 'The test runs asynchronously and leaves the editor open. Leave its viewport available until completion.'
        Write-Output "Read status, passed and errors in: $(Join-Path $ProjectRoot 'Saved\StreetAssembly\pie_validation.json')"
        Write-Output 'A successful launch is not a passed test; wait for status=complete and passed=true in the fresh report.'
        & $Editor $Project '-EnablePlugins=PythonScriptPlugin,EditorScriptingUtilities' "-ExecutePythonScript=$Script" -nosplash
        return
    }
    $Editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
    if (!(Test-Path -LiteralPath $Editor -PathType Leaf)) { throw "Editor commandlet not found: $Editor" }
    $ScriptName = if ($Mode -eq 'assemble') { 'assemble_street_scene.py' } else { 'import_street_assets.py' }
    $ReportName = if ($Mode -eq 'assemble') { 'assembly.json' } else { 'imports.json' }
    $Script = (Join-Path $PSScriptRoot $ScriptName).Replace('\', '/')
    $Report = Join-Path (Join-Path $ProjectRoot 'Saved\StreetAssembly') $ReportName
    $StartedUtc = (Get-Date).ToUniversalTime()
    & $Editor $Project '-EnablePlugins=PythonScriptPlugin,EditorScriptingUtilities' -run=pythonscript "-script=$Script" -unattended -NullRHI -nosplash
    if ($LASTEXITCODE -ne 0) {
        throw "Unreal exited with code $LASTEXITCODE. Inspect $Report and Saved/Logs/sakuradays.log."
    }
    if (!(Test-Path -LiteralPath $Report -PathType Leaf)) { throw "Unreal produced no report: $Report" }
    if ((Get-Item -LiteralPath $Report).LastWriteTimeUtc -lt $StartedUtc) {
        throw "Report is stale; this run is not verified: $Report"
    }
    $Result = Get-Content -LiteralPath $Report -Raw | ConvertFrom-Json
    if (!$Result.passed -or @($Result.errors).Count -gt 0) {
        throw ('Street workflow failed: ' + ($Result.errors -join '; '))
    }
    if ($Mode -eq 'plan') {
        Write-Output 'Import plan generated; this does not establish that assets have been imported or validated.'
    } else {
        Write-Output "Street workflow completed: $Mode"
    }
    Write-Output "Report: $Report"
    if ($Mode -eq 'assemble') {
        $Result | Select-Object map, passed, actor_count, backup, errors | ConvertTo-Json -Depth 5
    } else {
        $Result.assets | ConvertTo-Json -Depth 4
    }
} finally {
    $env:SAKURA_STREET_IMPORT_MODE = $oldMode
    $env:SAKURA_STREET_IMPORT_REVISION = $oldRevision
}
