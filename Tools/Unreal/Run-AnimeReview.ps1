param(
    [ValidateSet('before', 'pass1', 'pass2', 'pass3', 'references')]
    [string]$Review = 'before',
    [switch]$Apply,
    [string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8'
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$projectFile = Join-Path $projectRoot 'sakuradays.uproject'
$editorFile = Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor.exe'
$captureScript = Join-Path $PSScriptRoot 'capture_anime_review.py'
if (-not (Test-Path -LiteralPath $editorFile)) { throw "Editor not found: $editorFile" }
if (Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue) {
    throw 'Close Unreal Editor normally before this dedicated validation run; unsaved work is not closed automatically.'
}
if ($Apply -and $Review -eq 'before') { throw 'The baseline is capture-only.' }
$previousReview = $env:SAKURA_ANIME_REVIEW
$previousApply = $env:SAKURA_ANIME_APPLY
try {
    $env:SAKURA_ANIME_REVIEW = $Review
    $env:SAKURA_ANIME_APPLY = if ($Apply) { "refine_anime_$Review.py" } else { '' }
    if ($Apply -and -not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $env:SAKURA_ANIME_APPLY))) {
        throw 'The selected authoring pass does not exist.'
    }
    $startedUtc = [DateTime]::UtcNow
    $editorArguments = '"{0}" /Game/SakuraDays/Maps/L_SakuraStreet -EnablePlugins=PythonScriptPlugin,EditorScriptingUtilities -ExecutePythonScript="{1}" -nosplash' -f $projectFile, $captureScript
    $editorProcess = Start-Process -FilePath $editorFile -ArgumentList $editorArguments -WindowStyle Normal -Wait -PassThru
    if ($editorProcess.ExitCode -ne 0) { throw "Unreal exited with code $($editorProcess.ExitCode)." }
    $reportPath = Join-Path $projectRoot ".dream-loop/prompt13/$Review/validation.json"
    if (-not (Test-Path -LiteralPath $reportPath)) { throw 'No validation report was produced. Inspect Saved/Logs/sakuradays.log.' }
    if ((Get-Item -LiteralPath $reportPath).LastWriteTimeUtc -lt $startedUtc) { throw 'Stale validation report; this run did not complete.' }
    $report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
    if ($report.status -ne 'complete' -or -not $report.passed) {
        throw ('PIE validation failed: ' + ($report.errors -join '; '))
    }
    Write-Output "$Review : $($report.checks.Count) checks passed; genuine screenshots at .dream-loop/prompt13/$Review/"
} finally {
    $env:SAKURA_ANIME_REVIEW = $previousReview
    $env:SAKURA_ANIME_APPLY = $previousApply
}
