$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts\runtime.ps1')
$record = Join-Path $PSScriptRoot 'tmp\runtime\processes.json'
if (-not (Test-Path -LiteralPath $record)) { Write-Host 'No hay una ejecución registrada.'; return }
foreach ($entry in @(Get-Content -LiteralPath $record -Raw | ConvertFrom-Json)) {
    $process = Get-Process -Id $entry.id -ErrorAction SilentlyContinue
    # Avoid stopping an unrelated process if Windows has reused a recorded PID.
    if ($process -and $process.Path -eq $entry.path -and $process.StartTime.ToUniversalTime().Ticks -eq ([datetime]$entry.started).ToUniversalTime().Ticks) {
        Stop-juridIAProcessTree $process
    }
}
Remove-Item -LiteralPath $record
Write-Host 'Servicios de esta ejecución detenidos.'
