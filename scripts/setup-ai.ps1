[CmdletBinding()]
param(
    [string]$Model = 'qwen3.5:4b-q4_K_M',
    [switch]$SkipPull
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = Join-Path $projectRoot '.tools'
$runtimeDirectory = Join-Path $toolsRoot 'ollama'
$modelsDirectory = Join-Path $toolsRoot 'ollama-models'
$downloadDirectory = Join-Path $toolsRoot 'ollama-download'
$runtimeExecutable = Join-Path $runtimeDirectory 'ollama.exe'
$installationMarker = Join-Path $runtimeDirectory '.juridia-version'
$version = '0.40.0'
$archiveName = "ollama-windows-amd64-v$version.zip"
$archivePath = Join-Path $downloadDirectory $archiveName
$archiveUrl = "https://github.com/ollama/ollama/releases/download/v$version/ollama-windows-amd64.zip"
# Digest published for this release asset by the official ollama/ollama repository.
$expectedSha256 = '3623e256762ca89bd6fa99b0cc4106401919ce9df926411673e632e3ea287bb5'
$expectedArchiveBytes = 1468064949
$baseUri = 'http://127.0.0.1:11434'

New-Item -ItemType Directory -Force -Path $toolsRoot, $downloadDirectory, $modelsDirectory | Out-Null

$installed = (Test-Path -LiteralPath $runtimeExecutable) -and
    (Test-Path -LiteralPath $installationMarker) -and
    ((Get-Content -LiteralPath $installationMarker -Raw).Trim() -eq $version)

if (-not $installed) {
    $needsDownload = (-not (Test-Path -LiteralPath $archivePath)) -or
        ((Get-Item -LiteralPath $archivePath).Length -ne $expectedArchiveBytes)
    if ($needsDownload) {
        Write-Host "Descargando Ollama portable $version (aproximadamente 1.5 GB)..."
        & curl.exe --fail --location --retry 3 --continue-at - --output $archivePath $archiveUrl
        if ($LASTEXITCODE -ne 0) {
            throw 'No se pudo completar la descarga de Ollama. Ejecuta este script de nuevo para reanudarla.'
        }
    }
    Write-Host 'Verificando SHA-256 de la descarga oficial...'
    $actualSha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $expectedSha256) {
        throw "La descarga no coincide con el SHA-256 oficial. Revisa el archivo: $archivePath"
    }
    $runtimeProcesses = @(Get-Process -Name ollama -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -eq $runtimeExecutable
    })
    if ($runtimeProcesses.Count -gt 0) {
        throw 'Hay un proceso de este runtime en uso. Cierralo antes de reemplazar sus archivos.'
    }
    Write-Host 'Extrayendo el runtime local y sus bibliotecas de GPU...'
    Expand-Archive -LiteralPath $archivePath -DestinationPath $runtimeDirectory -Force
    if (-not (Test-Path -LiteralPath $runtimeExecutable)) {
        throw 'El paquete descargado no contiene ollama.exe en la ubicacion esperada.'
    }
    Set-Content -LiteralPath $installationMarker -Value $version -Encoding ascii
}

# These variables apply only to this process and the hidden server it starts.
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_MODELS = $modelsDirectory
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_CONTEXT_LENGTH = '4096'
$env:OLLAMA_NO_CLOUD = '1'

$serverVersion = $null
try {
    $serverVersion = Invoke-RestMethod -Uri "$baseUri/api/version" -TimeoutSec 3
} catch {
    $serverVersion = $null
}

if ($serverVersion) {
    $listeners = @(Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue)
    $ourListener = @($listeners | Where-Object {
        (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).Path -eq $runtimeExecutable
    })
    if ($ourListener.Count -eq 0) {
        throw 'El puerto 11434 ya lo utiliza otro Ollama. Cierra ese servicio para usar el runtime portable de juridIA.'
    }
    Write-Host "Ollama $($serverVersion.version) ya esta disponible en $baseUri."
} else {
    $listeners = @(Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -gt 0) {
        throw 'El puerto 11434 esta ocupado por otro proceso.'
    }
    $serverProcess = Start-Process -FilePath $runtimeExecutable -ArgumentList 'serve' `
        -WorkingDirectory $runtimeDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtimeDirectory 'server.stdout.log') `
        -RedirectStandardError (Join-Path $runtimeDirectory 'server.stderr.log')
    Set-Content -LiteralPath (Join-Path $runtimeDirectory 'server.pid') -Value $serverProcess.Id -Encoding ascii
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            $serverVersion = Invoke-RestMethod -Uri "$baseUri/api/version" -TimeoutSec 2
            break
        } catch {
            if ($serverProcess.HasExited) {
                throw "Ollama se cerro al iniciar. Revisa $runtimeDirectory\server.stderr.log"
            }
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $serverVersion) {
        throw "Ollama no respondio al iniciar. Revisa $runtimeDirectory\server.stderr.log"
    }
    Write-Host "Ollama $($serverVersion.version) iniciado en $baseUri (PID $($serverProcess.Id))."
}

if (-not $SkipPull) {
    $models = Invoke-RestMethod -Uri "$baseUri/api/tags" -TimeoutSec 10
    $installedModel = @($models.models | Where-Object { $_.name -eq $Model })
    if ($installedModel.Count -eq 0) {
        Write-Host "Descargando el modelo $Model..."
        & $runtimeExecutable pull $Model
        if ($LASTEXITCODE -ne 0) {
            throw 'No se pudo completar la descarga del modelo. Ejecuta este script de nuevo para reanudarla.'
        }
    }
    $models = Invoke-RestMethod -Uri "$baseUri/api/tags" -TimeoutSec 10
    $installedModel = @($models.models | Where-Object { $_.name -eq $Model })
    if ($installedModel.Count -eq 0) {
        throw "Ollama no reporta el modelo esperado: $Model"
    }
    Write-Host "Modelo listo: $Model"
    Write-Host "Digest: $($installedModel[0].digest)"
}

Write-Host "IA local disponible en $baseUri; modelos en $modelsDirectory."
