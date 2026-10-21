#define ReleaseVersion "0.2.1"
#ifdef SERVER_EDITION
 #define EditionName "QualityLite Servidor"
 #define OutputName "QualityLite-Server-Setup-0.2.1-x64"
#else
 #define EditionName "QualityLite Escritorio"
 #define OutputName "QualityLite-Desktop-Setup-0.2.1-x64"
#endif
[Setup]
AppId={{1D81C2D4-A850-4829-A70D-91048BC19BC8}
AppName={#EditionName}
AppVersion={#ReleaseVersion}
AppPublisher=QualityLite
DefaultDirName={autopf}\QualityLite
DefaultGroupName=QualityLite
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
PrivilegesRequired=admin
OutputDir=release
OutputBaseFilename={#OutputName}
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
Source: "apply_firewall.ps1"; DestDir: "{app}"
Source: "MANUAL.md"; DestDir: "{app}"
Source: "ARQUITECTURA.md"; DestDir: "{app}"
Source: "CORRECCION-0.2.0.md"; DestDir: "{app}"
Source: "CORRECCION-0.2.1.md"; DestDir: "{app}"
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
 NetworkPage: TInputQueryWizardPage;
 NetworkConsent: TInputOptionWizardPage;

function IsServerEdition: Boolean;
begin
#ifdef SERVER_EDITION
 Result := True;
#else
 Result := False;
#endif
end;

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
 if IsServerEdition then begin
  NetworkPage := CreateInputQueryPage(wpSelectDir, 'Configuracion del servidor', 'Direccion de escucha y puerto', 'Configure el acceso web. Una IP vacia conserva la configuracion anterior; en instalacion nueva se usa acceso local. Use 0.0.0.0 para todas las interfaces IPv4 o una IP del servidor.');
  NetworkPage.Add('Direccion IPv4 (vacia = conservar):',False);
  NetworkPage.Add('Puerto (vacio = automatico / conservar):',False);
  NetworkConsent := CreateInputOptionPage(NetworkPage.ID, 'Acceso a la red local', 'Autorice expresamente el acceso LAN', 'La regla se limita a la subred local en perfiles privado y dominio. No abre Internet ni modifica el router.',False,False);
  NetworkConsent.Add('Autorizar acceso LAN para la IP indicada');
 end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var Host: String; Port, I: Integer;
begin
 Result := True;
 if IsServerEdition then begin
  Host := Trim(NetworkPage.Values[0]);
  if CurPageID = NetworkPage.ID then begin
   for I := 1 to Length(Host) do
    if not (((Host[I] >= '0') and (Host[I] <= '9')) or (Host[I] = '.')) then begin
     MsgBox('Indique solamente una direccion IPv4.',mbError,MB_OK); Result := False; Exit;
    end;
   if Trim(NetworkPage.Values[1]) <> '' then begin
    Port := StrToIntDef(Trim(NetworkPage.Values[1]),0);
    if (Port < 1024) or (Port > 65535) then begin
     MsgBox('El puerto debe estar entre 1024 y 65535.',mbError,MB_OK); Result := False; Exit;
    end;
   end;
  end;
  if (CurPageID = NetworkConsent.ID) and (Host <> '') and (Host <> '127.0.0.1') and (not NetworkConsent.Values[0]) then begin
   MsgBox('Para escuchar en la red debe autorizar el acceso LAN, o usar 127.0.0.1 para acceso local.',mbError,MB_OK); Result := False;
  end;
 end;
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
var Host, Port: String;
begin
 if CurStep = ssPostInstall then begin
  try
   RunApplication('--self-test');
   RunChecked(ExpandConstant('{app}\QualityLiteSetupHelper.exe'), '--root "' + ExpandConstant('{commonappdata}\QualityLite') + '" --log "' + NativeLog + '"');
   if IsServerEdition then begin
    Host := Trim(NetworkPage.Values[0]); Port := Trim(NetworkPage.Values[1]);
    if (Host <> '') or (Port <> '') then begin
     if Host = '' then Host := 'keep';
     if Port = '' then Port := 'auto';
     RunApplication('--configure-network ' + Host + ' ' + Port);
    end;
   end;
   RunApplication('--init');
   RunApplication('--startup auto --username "NT AUTHORITY\LocalService" install');
   RunChecked(ExpandConstant('{sys}\sc.exe'), 'failure QualityLite reset= 86400 actions= restart/5000/restart/15000/restart/60000');
   RunChecked(ExpandConstant('{sys}\sc.exe'), 'failureflag QualityLite 1');
   RunApplication('--wait 30 start');
   RunApplication('--health');
   RunApplication('--publish-connection');
   if IsServerEdition then
    if (Trim(NetworkPage.Values[0]) <> '') or (Trim(NetworkPage.Values[1]) <> '') then
     RunChecked(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\apply_firewall.ps1') + '" -DataRoot "' + ExpandConstant('{commonappdata}\QualityLite') + '" -LogPath "' + DiagnosticLog + '"');
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
