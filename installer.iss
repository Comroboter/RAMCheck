; Ramwise installer (Inno Setup 6). build.bat compiles this automatically.
; Installs for the current user by default, no admin prompt. "Install for all users" is offered too.

#define AppName "Ramwise"
#define AppTagline "RAM analyzer & memory test"
; build.bat passes the real version from core.py with /DAppVersion=...
#ifndef AppVersion
  #define AppVersion "dev"
#endif
#define AppPublisher "Comroboter"
#define AppURL "https://github.com/Comroboter/Ramwise"
#define AppExe "Ramwise.exe"
; Never change this GUID, Windows uses it to recognize updates of the same app.
; It is still the one from when the app was called RAMCheck, so old installs get updated in place.
#define AppGuid "2C839633-C407-43C1-AFE8-DD917CD7A747"
#define AppIdSetup "{{" + AppGuid + "}"
#define UninstallKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\{" + AppGuid + "}_is1"

[Setup]
AppId={#AppIdSetup}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; when Ramwise is already installed, reuse its folder without asking again
DisableDirPage=auto
UsePreviousAppDir=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=Ramwise-Setup
SetupIconFile=ramwise.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
AppComments={#AppTagline}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; A running Ramwise is handled in [Code] (InitializeSetup): an update started from inside the app
; waits until the app has closed itself, a normal run asks the user to close it.
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Ramwise\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\Ramwise-cli.exe"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
; leftovers from when the app was called RAMCheck
Type: files; Name: "{app}\RAMCheck.exe"
Type: files; Name: "{app}\RAMCheck-cli.exe"
Type: files; Name: "{autoprograms}\RAMCheck.lnk"
Type: files; Name: "{autodesktop}\RAMCheck.lnk"

[Icons]
; AppUserModelID matches the one the app sets, so a pinned taskbar icon and the open window are one icon
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "Ramwise.App"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "Ramwise.App"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
; after an update started from inside the app: start the new version again
Filename: "{app}\{#AppExe}"; Flags: nowait postinstall runasoriginaluser; Check: RestartAfterUpdate

[Code]
{ Running the installer again when Ramwise is already installed shows a choice:
  update / repair (reinstall) or uninstall. }

var
  MaintPage: TInputOptionWizardPage;
  InstalledVersion, UninstallCmd: String;
  QuitQuietly: Boolean;

function FindInstall(): Boolean;
begin
  Result := False;
  InstalledVersion := '';
  if RegQueryStringValue(HKCU, '{#UninstallKey}', 'UninstallString', UninstallCmd) then
  begin
    RegQueryStringValue(HKCU, '{#UninstallKey}', 'DisplayVersion', InstalledVersion);
    Result := True;
  end
  else if RegQueryStringValue(HKLM, '{#UninstallKey}', 'UninstallString', UninstallCmd) then
  begin
    RegQueryStringValue(HKLM, '{#UninstallKey}', 'DisplayVersion', InstalledVersion);
    Result := True;
  end;
end;

function NextVersionPart(var S: String): Integer;
var
  P: Integer;
begin
  P := Pos('.', S);
  if P = 0 then
  begin
    Result := StrToIntDef(S, 0);
    S := '';
  end
  else
  begin
    Result := StrToIntDef(Copy(S, 1, P - 1), 0);
    Delete(S, 1, P);
  end;
end;

{ 1 if A is newer than B, -1 if older, 0 if equal }
function CompareVersions(A, B: String): Integer;
var
  I, X, Y: Integer;
begin
  Result := 0;
  for I := 1 to 4 do
  begin
    X := NextVersionPart(A);
    Y := NextVersionPart(B);
    if X > Y then
    begin
      Result := 1;
      Exit;
    end;
    if X < Y then
    begin
      Result := -1;
      Exit;
    end;
  end;
end;

{ True when the app started this installer for an update. /RESTARTAPP is what version 1.4 to 1.5.1 passed. }
function IsAppUpdate(): Boolean;
begin
  Result := (Pos('/UPDATE', Uppercase(GetCmdTail)) > 0) or (Pos('/RESTARTAPP', Uppercase(GetCmdTail)) > 0);
end;

function RestartAfterUpdate(): Boolean;
begin
  Result := WizardSilent and IsAppUpdate();
end;

function AppIsRunning(): Boolean;
begin
  Result := CheckForMutexes('RamwiseAppMutex,RAMCheckAppMutex');
end;

function InitializeSetup(): Boolean;
var
  Waited: Integer;
begin
  Result := True;
  { Ramwise closes itself right after starting the update, give it up to 30 seconds }
  Waited := 0;
  while AppIsRunning() and (Waited < 120) do
  begin
    Sleep(250);
    Waited := Waited + 1;
    if (not IsAppUpdate()) and (Waited >= 12) then
      Break;
  end;
  while AppIsRunning() do
  begin
    if WizardSilent then
    begin
      Log('Ramwise is still running after waiting, the update was not installed.');
      Result := False;
      Exit;
    end;
    if MsgBox('Ramwise is still running. Please close it, then click Retry.', mbError, MB_RETRYCANCEL) = IDCANCEL then
    begin
      Result := False;
      Exit;
    end;
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  while AppIsRunning() do
    if UninstallSilent or (MsgBox('Ramwise is still running. Please close it, then click Retry.',
                                  mbError, MB_RETRYCANCEL) = IDCANCEL) then
    begin
      Result := False;
      Exit;
    end;
end;

procedure InitializeWizard();
var
  Cmp: Integer;
  FirstOption, Shown: String;
begin
  if not FindInstall() then
    Exit;
  Shown := InstalledVersion;
  if Shown = '' then
    Shown := 'unknown';
  Cmp := CompareVersions('{#AppVersion}', InstalledVersion);
  if Cmp > 0 then
    FirstOption := 'Update to version {#AppVersion} (your settings are kept)'
  else if Cmp = 0 then
    FirstOption := 'Repair: reinstall version {#AppVersion} (your settings are kept)'
  else
    FirstOption := 'Install the older version {#AppVersion} over it';
  MaintPage := CreateInputOptionPage(wpWelcome,
    'Ramwise is already installed', 'What do you want to do?',
    'Version ' + Shown + ' is installed on this PC.', True, False);
  MaintPage.Add(FirstOption);
  MaintPage.Add('Uninstall Ramwise');
  MaintPage.SelectedValueIndex := 0;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if (MaintPage <> nil) and (CurPageID = MaintPage.ID) and (MaintPage.SelectedValueIndex = 1) then
  begin
    { ShellExec instead of Exec, so Windows can ask for admin rights if it was installed for all users }
    ShellExec('', RemoveQuotes(UninstallCmd), '', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
    QuitQuietly := True;
    WizardForm.Close;
    Result := False;
  end;
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  if QuitQuietly then
    Confirm := False;
end;

// Settings and API keys live in %APPDATA%\Ramwise, not in the program folder.
// Ask whether to delete them too, so no API key is left behind by accident.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Data: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Data := ExpandConstant('{userappdata}\Ramwise');
    if DirExists(Data) and not UninstallSilent then
      if MsgBox('Also delete your Ramwise settings, setup notes and saved API keys?',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(Data, True, True, True);
        DelTree(ExpandConstant('{userappdata}\RAMCheck'), True, True, True);  { from the old name, if any }
      end;
  end;
end;
