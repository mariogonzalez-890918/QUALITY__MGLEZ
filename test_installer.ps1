# Exclusivo para runner Windows desechable de GitHub Actions, no ejecutar en producción.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Esta prueba requiere un runner dedicado de GitHub Actions.' }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'El runner necesita elevación.' }
$dataRoot = Join-Path $env:ProgramData 'QualityLite'
if ((Get-Service QualityLite -ErrorAction SilentlyContinue) -or (Test-Path -LiteralPath $dataRoot)) { throw 'El runner ya contiene QualityLite. No se tocarán datos existentes.' }
$appRoot = Join-Path $env:RUNNER_TEMP 'QualityLite Installation Test'
$setup = Join-Path $PSScriptRoot 'release\QualityLite-Setup-0.1.2-x64.exe'
$report = Join-Path $PSScriptRoot 'release\installer-test-result.txt'
function Install-QualityLite([string]$logName) {
 $logPath = Join-Path $PSScriptRoot ('release\' + $logName)
 $arguments = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="' + $appRoot + '"'),('/LOG="' + $logPath + '"'))
 $installed = Start-Process -FilePath $setup -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
 if ($installed.ExitCode -ne 0) { throw "Instalación fallida: $($installed.ExitCode). Consulte $logPath" }
 $service = Get-Service QualityLite
 if ($service.Status -ne 'Running') { throw 'El servicio no está ejecutándose.' }
 $details = Get-CimInstance Win32_Service -Filter "Name='QualityLite'"
 if ($details.StartMode -ne 'Auto' -or $details.StartName -ne 'NT AUTHORITY\LocalService') { throw 'Cuenta o inicio incorrectos.' }
 $cfg = Get-Content -LiteralPath (Join-Path $dataRoot 'server.json') -Raw | ConvertFrom-Json
 $health = Invoke-RestMethod -Uri ("http://127.0.0.1:" + $cfg.port + '/health')
 if ($health.status -ne 'ok') { throw 'Salud HTTP fallida.' }
 $public = Get-Content -LiteralPath (Join-Path $appRoot 'connection.json') -Raw | ConvertFrom-Json
 if ($public.port -ne $cfg.port) { throw 'URL publica no coincide con el servicio.' }
}
try {
 Install-QualityLite 'install-clean.log'
 'OK: instalación limpia, LocalService, inicio automático y salud HTTP' | Set-Content $report
 $marker = Join-Path $dataRoot 'prueba-conservacion.txt'
 'Conservar información' | Set-Content -LiteralPath $marker
 $hashBefore = (Get-FileHash (Join-Path $dataRoot 'qualitylite.db')).Hash
 Restart-Service QualityLite
 & (Join-Path $appRoot 'QualityLite.exe') --health
 if ($LASTEXITCODE -ne 0) { throw 'Fallo después de reiniciar el servicio.' }
 'OK: reinicio controlado y salud' | Add-Content $report
 Install-QualityLite 'install-update.log'
 if ((Get-Content -LiteralPath $marker) -ne 'Conservar información') { throw 'Actualización perdió archivo.' }
 if ((Get-FileHash (Join-Path $dataRoot 'qualitylite.db')).Hash -ne $hashBefore) { throw 'Actualización modificó inesperadamente la base vacía.' }
 'OK: actualización conserva datos' | Add-Content $report
 $uninstaller = Start-Process -FilePath (Join-Path $appRoot 'unins000.exe') -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -WindowStyle Hidden -Wait -PassThru
 if ($uninstaller.ExitCode -ne 0) { throw 'Desinstalación fallida.' }
 if (-not (Test-Path -LiteralPath $marker) -or -not (Test-Path -LiteralPath (Join-Path $dataRoot 'qualitylite.db'))) { throw 'Desinstalación perdió datos.' }
 if (Get-Service QualityLite -ErrorAction SilentlyContinue) { throw 'El servicio permanece después de desinstalar.' }
 'OK: desinstalación conserva datos y elimina servicio' | Add-Content $report
} catch {
 $_ | Out-String | Add-Content $report
 throw
} finally {
 if (Test-Path -LiteralPath (Join-Path $dataRoot 'logs')) { Copy-Item -LiteralPath (Join-Path $dataRoot 'logs') -Destination (Join-Path $PSScriptRoot 'release\service-test-logs') -Recurse -Force }
 if (Test-Path -LiteralPath (Join-Path $dataRoot 'launcher-error.log')) { Copy-Item -LiteralPath (Join-Path $dataRoot 'launcher-error.log') -Destination (Join-Path $PSScriptRoot 'release\launcher-error.log') }
}
