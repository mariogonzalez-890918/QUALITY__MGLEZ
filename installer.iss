[Setup]
AppId={{1D81C2D4-A850-4829-A70D-91048BC19BC8}
AppName=QualityLite
AppVersion=0.1.1
AppPublisher=QualityLite
DefaultDirName={autopf}\QualityLite
DefaultGroupName=QualityLite
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=admin
OutputDir=release
OutputBaseFilename=QualityLite-Setup-0.1.1-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\QualityLite.exe
CloseApplications=yes
SetupLogging=yes
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
[Dirs]
Name: "{commonappdata}\QualityLite"
[Files]
Source: "dist\QualityLite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "manage.ps1"; DestDir: "{app}"
Source: "MANUAL.md"; DestDir: "{app}"
Source: "ARQUITECTURA.md"; DestDir: "{app}"
Source: "THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"
[Icons]
Name: "{group}\Abrir QualityLite"; Filename: "{app}\QualityLite.exe"; Parameters: "--open"
Name: "{commondesktop}\QualityLite"; Filename: "{app}\QualityLite.exe"; Parameters: "--open"
Name: "{group}\Registros y datos"; Filename: "{commonappdata}\QualityLite"
Name: "{group}\Administrar servicio"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""Start-Process powershell.exe -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File """"{app}\manage.ps1""""'"""
Name: "{group}\Manual"; Filename: "{app}\MANUAL.md"
[Run]
Filename: "{app}\QualityLite.exe"; Parameters: "--open"; Description: "Abrir configuración inicial"; Flags: postinstall nowait skipifsilent runasoriginaluser
[UninstallRun]
Filename: "{app}\QualityLite.exe"; Parameters: "--wait 30 stop"; Flags: runhidden; RunOnceId: "StopQualityLite"
Filename: "{app}\QualityLite.exe"; Parameters: "remove"; Flags: runhidden; RunOnceId: "RemoveQualityLite"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""QualityLite HTTP LAN"""; Flags: runhidden; RunOnceId: "FirewallQualityLite"
[Code]
procedure RunChecked(FileName, Params: String);
var Code: Integer;
begin
 if not Exec(FileName, Params, '', SW_HIDE, ewWaitUntilTerminated, Code) then RaiseException('No se pudo ejecutar: ' + FileName);
 Log('QualityLite: ' + FileName + ' ' + Params + ' terminó con código ' + IntToStr(Code));
 if Code <> 0 then RaiseException('Falló ' + ExtractFileName(FileName) + ' ' + Params + ' (código ' + IntToStr(Code) + '). Consulte launcher-error.log y logs\service-commands.log en ProgramData\QualityLite; si no se pudo escribir allí, consulte %TEMP%\QualityLite-install-error.log.');
end;
function PrepareToInstall(var NeedsRestart: Boolean): String;
var Code: Integer;
begin
 Result := '';
 if FileExists(ExpandConstant('{app}\QualityLite.exe')) then begin
  Exec(ExpandConstant('{app}\QualityLite.exe'), '--wait 30 stop', '', SW_HIDE, ewWaitUntilTerminated, Code);
  if (Code <> 0) and (Code <> 1060) and (Code <> 1062) then
   Result := 'No se pudo detener QualityLite (código ' + IntToStr(Code) + '). Consulte los registros antes de actualizar.';
 end;
end;
procedure CurStepChanged(CurStep: TSetupStep);
var Code: Integer;
begin
 if CurStep = ssPostInstall then begin
  RunChecked(ExpandConstant('{app}\QualityLite.exe'), '--secure-data');
  RunChecked(ExpandConstant('{app}\QualityLite.exe'), '--init');
  RunChecked(ExpandConstant('{app}\QualityLite.exe'), '--startup auto --username "NT AUTHORITY\LocalService" install');
  RunChecked(ExpandConstant('{sys}\sc.exe'), 'failure QualityLite reset= 86400 actions= restart/5000/restart/15000/restart/60000');
  RunChecked(ExpandConstant('{sys}\sc.exe'), 'failureflag QualityLite 1');
  RunChecked(ExpandConstant('{app}\QualityLite.exe'), '--wait 30 start');
  RunChecked(ExpandConstant('{app}\QualityLite.exe'), '--health');
 end;
end;
