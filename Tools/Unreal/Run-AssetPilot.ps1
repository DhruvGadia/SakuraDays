param(
    [ValidateSet('plan','import','validate','reimport','pie')][string]$Mode='plan',
    [string]$Revision='',
    [string]$EngineRoot='C:\Program Files\Epic Games\UE_5.8'
)
$ErrorActionPreference='Stop'
$ProjectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$Project=Join-Path $ProjectRoot 'sakuradays.uproject'
$oldMode=$env:SAKURA_IMPORT_MODE
$oldRevision=$env:SAKURA_IMPORT_REVISION
try {
    $env:SAKURA_IMPORT_MODE=if ($Mode -eq 'pie') { 'import' } else { $Mode }
    $env:SAKURA_IMPORT_REVISION=$Revision
    if ($Mode -eq 'pie') {
        $Editor=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
        $Script=(Join-Path $PSScriptRoot 'test_import_pilot.py').Replace('\','/')
        & $Editor $Project '-EnablePlugins=PythonScriptPlugin,EditorScriptingUtilities' "-ExecutePythonScript=$Script" -nosplash
    } else {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'Close Unreal Editor normally before a separate import commandlet, to avoid concurrent package edits.' }
        $Editor=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
        $Script=(Join-Path $PSScriptRoot 'import_pilot.py').Replace('\','/')
        $Started=Get-Date
        & $Editor $Project '-EnablePlugins=PythonScriptPlugin,EditorScriptingUtilities' -run=pythonscript "-script=$Script" -unattended -NullRHI -nosplash
        if ($LASTEXITCODE -ne 0) { throw "Unreal exited with code $LASTEXITCODE; inspect its log." }
        $Report=Join-Path $ProjectRoot 'Saved\AssetImportPilot\latest.json'
        if (!(Test-Path -LiteralPath $Report)) { throw 'No import report produced; inspect Unreal logs.' }
        if ((Get-Item -LiteralPath $Report).LastWriteTime -lt $Started) { throw 'Import report is stale; inspect Unreal logs.' }
        $Result=Get-Content -LiteralPath $Report -Raw | ConvertFrom-Json
        if (!$Result.passed) { throw ('Pilot failed: '+($Result.errors -join '; ')) }
        $Result.results | ConvertTo-Json -Depth 7
    }
} finally {
    $env:SAKURA_IMPORT_MODE=$oldMode
    $env:SAKURA_IMPORT_REVISION=$oldRevision
}
