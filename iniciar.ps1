[CmdletBinding()]
param([switch]$Demo, [switch]$ConCuenta, [switch]$SinIA, [switch]$SegundoPlano)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts\runtime.ps1')
if ($Demo -and $ConCuenta) { throw 'Elige -Demo o -ConCuenta, no ambos.' }
$projectDirectory = $PSScriptRoot
$frontendDirectory = Join-Path $projectDirectory 'frontend'
$backendDirectory = Join-Path $projectDirectory 'backend'
$pythonExecutable = Join-Path $backendDirectory '.venv\Scripts\python.exe'
$viteExecutable = Join-Path $frontendDirectory 'node_modules\vite\bin\vite.js'
$ollamaExecutable = Join-Path $projectDirectory '.tools\ollama\ollama.exe'
$logDirectory = Join-Path $projectDirectory 'tmp\runtime'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
if (-not (Test-Path -LiteralPath $viteExecutable)) {
    throw 'Primero instala las dependencias: cd frontend; npm ci'
}
if (-not $Demo -and -not (Test-Path -LiteralPath $pythonExecutable)) { throw 'Prepara el entorno Python siguiendo README.md.' }
$nodeExecutable = (Get-Command node -ErrorAction Stop).Source
$started = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$variables = @('VITE_DATA_MODE', 'OLLAMA_HOST', 'OLLAMA_MODELS', 'OLLAMA_NUM_PARALLEL', 'OLLAMA_MAX_LOADED_MODELS', 'OLLAMA_NO_CLOUD')
$previous = @{}
foreach ($name in $variables) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$ready = $false

function Test-LocalPort([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try { return $client.ConnectAsync('127.0.0.1', $Port).Wait(400) -and $client.Connected }
    catch { return $false } finally { $client.Dispose() }
}
function Wait-Service([string]$Uri, [System.Diagnostics.Process]$Process) {
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        if ($Process.HasExited) { throw "El servicio se cerró. Revisa los registros en $logDirectory" }
        try { return Invoke-RestMethod -Uri $Uri -TimeoutSec 5 } catch { Start-Sleep -Milliseconds 500 }
    }
    throw "No respondió $Uri. Revisa los registros en $logDirectory"
}
try {
    if (Test-LocalPort 5173) { throw 'El puerto 5173 está ocupado. Abre http://127.0.0.1:5173 si juridIA ya está ejecutándose.' }
    if (-not $Demo) {
        if (Test-LocalPort 8000) { throw 'El puerto 8000 está ocupado. Detén la instancia anterior antes de iniciar otra.' }
        if (-not $SinIA -and (Test-Path -LiteralPath $ollamaExecutable) -and -not (Test-LocalPort 11434)) {
            $env:OLLAMA_HOST = '127.0.0.1:11434'
            $env:OLLAMA_MODELS = Join-Path $projectDirectory '.tools\ollama-models'
            $env:OLLAMA_NUM_PARALLEL = '1'
            $env:OLLAMA_MAX_LOADED_MODELS = '1'
            $env:OLLAMA_NO_CLOUD = '1'
            $ollama = Start-Process -FilePath $ollamaExecutable -ArgumentList 'serve' -WorkingDirectory $projectDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory 'ollama.out.log') -RedirectStandardError (Join-Path $logDirectory 'ollama.err.log')
            $started.Add($ollama)
            try { Wait-Service 'http://127.0.0.1:11434/api/version' $ollama | Out-Null }
            catch {
                Stop-juridIAProcessTree $ollama
                Write-Warning 'Ollama no pudo iniciar. Continuando con búsqueda documental y plantillas sin IA.'
            }
        }
        $backend = Start-Process -FilePath $pythonExecutable -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $backendDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory 'api.out.log') -RedirectStandardError (Join-Path $logDirectory 'api.err.log')
        $started.Add($backend)
        $health = Wait-Service 'http://127.0.0.1:8000/api/health' $backend
        if (-not $health.database.connected) { throw 'La base de datos no está conectada. Revisa backend/.env y el servicio MySQL.' }
        Write-Host "Base de datos: $($health.database.engine). IA disponible: $($health.ai.available)."
        $env:VITE_DATA_MODE = 'api'
    } else {
        $env:VITE_DATA_MODE = 'demo'
    }
    $frontend = Start-Process -FilePath $nodeExecutable -ArgumentList ('"{0}" --host 127.0.0.1' -f $viteExecutable) -WorkingDirectory $frontendDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory 'web.out.log') -RedirectStandardError (Join-Path $logDirectory 'web.err.log')
    $started.Add($frontend)
    Wait-Service 'http://127.0.0.1:5173/' $frontend | Out-Null
    $records = @($started | ForEach-Object { [PSCustomObject]@{ id = $_.Id; path = $_.Path; started = $_.StartTime.ToUniversalTime().ToString('o') } })
    ConvertTo-Json -InputObject $records | Set-Content -LiteralPath (Join-Path $logDirectory 'processes.json') -Encoding utf8
    $ready = $true
    Write-Host 'juridIA listo: http://127.0.0.1:5173/'
    if ($SegundoPlano) { Write-Host 'Ejecutándose en segundo plano. Para detenerlo: ./detener.ps1' }
    else { Write-Host 'Ctrl+C para detener los servicios iniciados aquí.'; while (-not $frontend.HasExited) { Start-Sleep -Seconds 1 } }
} finally {
    foreach ($name in $variables) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
    if (-not $SegundoPlano -or -not $ready) {
        foreach ($process in $started) { Stop-juridIAProcessTree $process }
    }
}
