[Setup]
AppId={{1D81C2D4-A850-4829-A70D-91048BC19BC8}
AppName=QualityLite
AppVersion=0.1.2
AppPublisher=QualityLite
DefaultDirName={autopf}\QualityLite
DefaultGroupName=QualityLite
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
PrivilegesRequired=admin
OutputDir=release
OutputBaseFilename=QualityLite-Setup-0.1.2-x64
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
Source: "build\native\QualityLiteSetupHelper.exe"; DestDir: "{app}"; Flags: ignoreversion
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
Filename: "{app}\QualityLite.exe"; Parameters: "--open"; Description: "Abrir configuración inicial"; Flags: postinstall nowait skipifsilent runasoriginaluser; Check: SetupSucceeded
[UninstallRun]
Filename: "{app}\QualityLite.exe"; Parameters: "--wait 30 stop"; Flags: runhidden; RunOnceId: "StopQualityLite"
Filename: "{app}\QualityLite.exe"; Parameters: "remove"; Flags: runhidden; RunOnceId: "RemoveQualityLite"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""QualityLite HTTP LAN"""; Flags: runhidden; RunOnceId: "FirewallQualityLite"
[Code]
var
 DiagnosticLog: String;
 NativeLog: String;
 InstallFailed: Boolean;
 InstallError: String;

function SetupSucceeded: Boolean;
begin
 Result := not InstallFailed;
end;

function LogTail(Path: String): String;
var Contents: AnsiString;
begin
 Result := '';
 if LoadStringFromFile(Path, Contents) then begin
  Result := UTF8Decode(Contents);
  if Length(Result) > 4500 then Delete(Result, 1, Length(Result)-4500);
 end;
end;

procedure InitializeWizard;
var Stamp, Directory: String;
begin
 Stamp := GetDateTimeString('yyyymmdd-hhnnss', '-', ':');
 Directory := ExpandConstant('{commonappdata}\QualityLite-SetupLogs');
 if not ForceDirectories(Directory) then Directory := GetEnv('TEMP');
 DiagnosticLog := AddBackslash(Directory) + 'QualityLite-runtime-' + Stamp + '.log';
 NativeLog := AddBackslash(Directory) + 'QualityLite-native-' + Stamp + '.log';
 InstallFailed := False;
 Log('Diagnostico de arranque: ' + DiagnosticLog);
 Log('Diagnostico nativo: ' + NativeLog);
end;

procedure RunChecked(FileName, Params: String);
var Code: Integer;
begin
 if not Exec(FileName, Params, '', SW_HIDE, ewWaitUntilTerminated, Code) then RaiseException('No se pudo ejecutar: ' + FileName);
 Log('QualityLite: ' + FileName + ' ' + Params + ' terminó con código ' + IntToStr(Code));
 if Code <> 0 then RaiseException('No se pudo completar: ' + ExtractFileName(FileName) + ' (codigo ' + IntToStr(Code) + ').' + #13#10 + LogTail(NativeLog) + #13#10 + LogTail(DiagnosticLog));
end;

procedure RunApplication(Params: String);
begin
 RunChecked(ExpandConstant('{app}\QualityLite.exe'), '--data-root "' + ExpandConstant('{commonappdata}\QualityLite') + '" --diagnostic-log "' + DiagnosticLog + '" ' + Params);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
 Result := '';
 try
  ExtractTemporaryFile('QualityLiteSetupHelper.exe');
  RunChecked(ExpandConstant('{tmp}\QualityLiteSetupHelper.exe'), '--stop-service --log "' + NativeLog + '"');
 except
  Result := GetExceptionMessage + #13#10 + 'Registro: ' + NativeLog;
 end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
 if CurStep = ssPostInstall then begin
  try
   RunApplication('--self-test');
   RunChecked(ExpandConstant('{app}\QualityLiteSetupHelper.exe'), '--root "' + ExpandConstant('{commonappdata}\QualityLite') + '" --log "' + NativeLog + '"');
   RunApplication('--init');
   RunApplication('--startup auto --username "NT AUTHORITY\LocalService" install');
   RunChecked(ExpandConstant('{sys}\sc.exe'), 'failure QualityLite reset= 86400 actions= restart/5000/restart/15000/restart/60000');
   RunChecked(ExpandConstant('{sys}\sc.exe'), 'failureflag QualityLite 1');
   RunApplication('--wait 30 start');
   RunApplication('--health');
   RunApplication('--publish-connection');
  except
   InstallFailed := True;
   InstallError := GetExceptionMessage;
   Log('INSTALACION NO COMPLETADA: ' + InstallError);
   SuppressibleMsgBox('QualityLite no pudo completar la configuracion.' + #13#10 + InstallError + #13#10 + 'Registros: ' + NativeLog + #13#10 + DiagnosticLog + #13#10 + 'Los datos existentes no se han eliminado.', mbError, MB_OK, IDOK);
  end;
 end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
 if (CurPageID = wpFinished) and InstallFailed then begin
  WizardForm.FinishedHeadingLabel.Caption := 'Configuracion de QualityLite pendiente';
  WizardForm.FinishedLabel.Caption := 'No se pudo iniciar la aplicacion. Consulte los registros indicados; no es necesario borrar sus datos.';
  WizardForm.RunList.Visible := False;
 end;
end;

function GetCustomSetupExitCode: Integer;
begin
 if InstallFailed then Result := 20 else Result := 0;
end;
