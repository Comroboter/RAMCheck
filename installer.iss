; RAMCheck installer (Inno Setup 6). build.bat compiles this automatically.
; Installs for the current user by default, no admin prompt. "Install for all users" is offered too.

#define AppName "RAMCheck"
#define AppVersion "1.0"
#define AppPublisher "Comroboter"
#define AppURL "https://github.com/Comroboter/RAMCheck"
#define AppExe "RAMCheck.exe"

[Setup]
; Never change the AppId, Windows uses it to recognize updates of the same app
AppId={{2C839633-C407-43C1-AFE8-DD917CD7A747}
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
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=RAMCheck-Setup-{#AppVersion}
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
