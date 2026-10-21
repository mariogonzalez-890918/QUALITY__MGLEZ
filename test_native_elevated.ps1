# Validación aislada del preparador nativo; no cambia el servicio ni datos instalados.
$ErrorActionPreference = 'Stop'
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Se requiere elevación para validar las ACL de producción.' }
$sandboxRoot = Join-Path $env:TEMP ('QualityLite-native-test-' + [guid]::NewGuid().ToString('N'))
$dataRoot = Join-Path $sandboxRoot 'Datos de prueba á'
$filesRoot = Join-Path $dataRoot 'evidencias'
New-Item -ItemType Directory -Path $filesRoot -Force | Out-Null
$filePath = Join-Path $filesRoot 'original.txt'
'Conservar evidencia de prueba' | Set-Content -LiteralPath $filePath -Encoding utf8
$hashBefore = (Get-FileHash -LiteralPath $filePath).Hash
$helper = Join-Path $PSScriptRoot 'build\native\QualityLiteSetupHelper.exe'
$logPath = Join-Path $sandboxRoot 'native.log'
& $helper --root $dataRoot --log $logPath
if ($LASTEXITCODE -ne 0) { throw "Preparador falló con código $LASTEXITCODE. Log: $logPath" }
if ((Get-FileHash -LiteralPath $filePath).Hash -ne $hashBefore) { throw 'El contenido de prueba cambió.' }
$expected = @('S-1-5-18','S-1-5-19','S-1-5-32-544') | Sort-Object
foreach ($target in @($dataRoot,$filesRoot,$filePath)) {
 $acl = Get-Acl -LiteralPath $target
 $actual = @($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | ForEach-Object { $_.IdentityReference.Value }) | Sort-Object
 if (@(Compare-Object $expected $actual).Count -ne 0) { throw "ACL inesperada: $target" }
 if (-not $acl.AreAccessRulesProtected) { throw "ACL no protegida: $target" }
}
& $helper --root $dataRoot --log $logPath
if ($LASTEXITCODE -ne 0) { throw 'Reaplicar permisos no es idempotente.' }
$result = [ordered]@{
 version='0.1.2'; windows=(Get-CimInstance Win32_OperatingSystem).Caption
 result='passed'; tests=@('ACL reales de directorio y archivo','Solo SYSTEM, Administradores y LocalService','Conservacion del archivo original','Rutas con espacios y caracteres no ASCII','Reaplicacion idempotente')
}
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'release\prueba-nativa-elevada.json') -Encoding utf8
Write-Output 'Validación nativa elevada aprobada.'
