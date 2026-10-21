# Prueba autorizada de actualización local de QualityLite, sin eliminar datos.
$ErrorActionPreference = 'Stop'
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Se requiere elevacion para comprobar datos privados.' }
$root = Join-Path $env:ProgramData 'QualityLite'
$newExecutable = Join-Path $PSScriptRoot 'dist\QualityLite\QualityLite.exe'
$setup = Join-Path $PSScriptRoot 'release\QualityLite-Desktop-Setup-0.2.0-x64.exe'
$hasDatabase = Test-Path -LiteralPath (Join-Path $root 'qualitylite.db')
$before = $null
$hashes = @{}
if ($hasDatabase) {
 $raw = & $newExecutable --data-root $root --data-status
 if ($LASTEXITCODE -ne 0) { throw 'No se pudo comprobar la base existente antes de actualizar.' }
 $before = $raw | ConvertFrom-Json
 foreach ($name in @('secret.key','server.json')) {
  $file = Join-Path $root $name
  if (Test-Path -LiteralPath $file) { $hashes[$name] = (Get-FileHash -LiteralPath $file).Hash }
 }
}
$logPath = Join-Path $PSScriptRoot 'release\install-local-0.2.0.log'
$install = Start-Process -FilePath $setup -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="' + $logPath + '"') -WindowStyle Hidden -Wait -PassThru
if ($install.ExitCode -ne 0) { throw "Instalacion fallo con codigo $($install.ExitCode). Consulte $logPath" }
$service = Get-CimInstance Win32_Service -Filter "Name='QualityLite'"
if ($service.State -ne 'Running' -or $service.StartMode -ne 'Auto' -or $service.StartName -ne 'NT AUTHORITY\LocalService') { throw 'Servicio no configurado correctamente.' }
$appRoot = Join-Path $env:ProgramFiles 'QualityLite'
$installed = Join-Path $appRoot 'QualityLite.exe'
$raw = & $installed --data-root $root --data-status
if ($LASTEXITCODE -ne 0) { throw 'No se puede verificar la base instalada.' }
$after = $raw | ConvertFrom-Json
if ($before) {
 foreach ($table in @('users','items','files','settings')) {
  if ($before.$table -ne $after.$table) { throw "Cambió el numero de elementos en $table" }
 }
 foreach ($name in $hashes.Keys) {
  if ((Get-FileHash -LiteralPath (Join-Path $root $name)).Hash -ne $hashes[$name]) { throw "La actualizacion altero $name" }
 }
}
$public = Get-Content -LiteralPath (Join-Path $appRoot 'connection.json') -Raw | ConvertFrom-Json
$health = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $public.port + '/health')
if ($health.status -ne 'ok') { throw 'La aplicacion no responde por HTTP.' }
$result = [ordered]@{version='0.2.0'; result='passed'; windows=(Get-CimInstance Win32_OperatingSystem).Caption; upgraded_existing=$hasDatabase; service_state=$service.State; service_start=$service.StartMode; service_account=$service.StartName; data_integrity=$after.integrity; original_counts_preserved=$true; original_key_and_config_preserved=$true; url=('http://127.0.0.1:'+$public.port+'/')}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'release\prueba-instalacion-0.2.0.json') -Encoding utf8
