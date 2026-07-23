; Velo Installer - Inno Setup 6
; Build:  .\scripts\build.ps1 -Clean
;         then .\scripts\build.ps1 -Installer
; Or:     .\scripts\build.ps1 -Clean -Installer

#define AppName      "Velo"
#define AppVersion   "1.0.3"
#define AppPublisher "aech"
#define AppURL       "https://github.com/aechXIII/Velo"
#define AppExeName   "Velo.exe"
; Install under LocalAppData (no UAC)
#define AppInstDir   "{localappdata}\Velo"

[Setup]
AppId={{E7C3A91B-2D54-4F18-9B6E-0A1C8D4F7E22}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={#AppInstDir}
DisableDirPage=yes
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=Velo-Setup-{#AppVersion}
SetupIconFile=..\assets\velo.ico
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
CloseApplications=yes
CloseApplicationsFilter=*.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\velo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\velo.ico"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\velo.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/f /im {#AppExeName}"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
; App install dir only - user config in %APPDATA%\Velo is kept
Type: files; Name: "{app}\{#AppExeName}"
Type: files; Name: "{app}\velo.ico"
Type: dirifempty; Name: "{app}"
