# Ejecutado con elevación mediante el acceso directo del instalador.
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:ProgramData 'QualityLite'
Write-Host 'QualityLite: 1 Estado, 2 Iniciar, 3 Detener, 4 Reiniciar, 5 Aplicar red y reiniciar'
$choice = Read-Host 'Opción'
switch ($choice) {
 '1' { Get-Service -Name QualityLite }
 '2' { Start-Service -Name QualityLite }
 '3' { Stop-Service -Name QualityLite }
 '4' { Restart-Service -Name QualityLite }
 '5' {
  $config = Get-Content -LiteralPath (Join-Path $root 'server.json') -Raw | ConvertFrom-Json
  Get-NetFirewallRule -DisplayName 'QualityLite HTTP LAN' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
  if ($config.host -ne '127.0.0.1') {
   New-NetFirewallRule -DisplayName 'QualityLite HTTP LAN' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $config.port -Profile Private,Domain -RemoteAddress LocalSubnet -Program (Join-Path $PSScriptRoot 'QualityLite.exe')
  }
  Restart-Service -Name QualityLite
 }
 default { Write-Host 'Opción inválida' }
}
Read-Host 'Pulse Entrar para cerrar'
