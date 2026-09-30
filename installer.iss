; RAMCheck installer (Inno Setup 6). build.bat compiles this automatically.
; Installs for the current user by default, no admin prompt. "Install for all users" is offered too.

#define AppName "RAMCheck"
; build.bat passes the real version from core.py with /DAppVersion=...
#ifndef AppVersion
  #define AppVersion "dev"
#endif
#define AppPublisher "Comroboter"
#define AppURL "https://github.com/Comroboter/RAMCheck"
#define AppExe "RAMCheck.exe"
; Never change this GUID, Windows uses it to recognize updates of the same app
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
; when RAMCheck is already installed, reuse its folder without asking again
DisableDirPage=auto
UsePreviousAppDir=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=RAMCheck-Setup
SetupIconFile=ramcheck.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; closes a running RAMCheck before updating or uninstalling
AppMutex=RAMCheckAppMutex
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\RAMCheck\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\RAMCheck-cli.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
{ Running the installer again when RAMCheck is already installed shows a choice:
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
    'RAMCheck is already installed', 'What do you want to do?',
    'Version ' + Shown + ' is installed on this PC.', True, False);
  MaintPage.Add(FirstOption);
  MaintPage.Add('Uninstall RAMCheck');
  MaintPage.SelectedValueIndex := 0;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if (MaintPage <> nil) and (CurPageID = MaintPage.ID) and (MaintPage.SelectedValueIndex = 1) then
  begin
    { ShellExec instead of Exec, so Windows can ask for admin rights if RAMCheck was installed for all users }
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

// Settings and API keys live in %APPDATA%\RAMCheck, not in the program folder.
// Ask whether to delete them too, so no API key is left behind by accident.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Data: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Data := ExpandConstant('{userappdata}\RAMCheck');
    if DirExists(Data) and not UninstallSilent then
      if MsgBox('Also delete your RAMCheck settings, setup notes and saved API keys?',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(Data, True, True, True);
  end;
end;
