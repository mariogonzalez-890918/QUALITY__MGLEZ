param([Parameter(Mandatory=$true)][string]$DataRoot,[string]$LogPath)
$ErrorActionPreference = 'Stop'
try {
 $cfg = Get-Content -LiteralPath (Join-Path $DataRoot 'server.json') -Raw | ConvertFrom-Json
 [void][System.Net.IPAddress]::Parse($cfg.host)
 if ([int]$cfg.port -lt 1024 -or [int]$cfg.port -gt 65535) { throw 'Puerto de red inválido' }
 Get-NetFirewallRule -DisplayName 'QualityLite HTTP LAN' -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction Stop
 if ($cfg.host -ne '127.0.0.1') {
  $rule = @{DisplayName='QualityLite HTTP LAN';Direction='Inbound';Action='Allow';Protocol='TCP';LocalPort=[int]$cfg.port;Profile=@('Private','Domain');RemoteAddress='LocalSubnet';Program=(Join-Path $PSScriptRoot 'QualityLite.exe')}
  if ($cfg.host -ne '0.0.0.0') { $rule.LocalAddress=$cfg.host }
  New-NetFirewallRule @rule | Out-Null
 }
} catch {
 if ($LogPath) { $_ | Out-String | Add-Content -LiteralPath $LogPath -Encoding UTF8 }
 throw
}
