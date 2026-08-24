; Velo Installer - Inno Setup 6
; Build:  .\scripts\build.ps1 -Clean
;         then .\scripts\build.ps1 -Installer
; Or:     .\scripts\build.ps1 -Clean -Installer

#define AppName      "Velo"
#define AppVersion   "2.3.3"
#define AppPublisher "aechXIII"
#define AppURL       "https://github.com/aechXIII/Velo"
#define AppSupportURL "https://github.com/aechXIII/Velo/issues"
#define AppUpdatesURL "https://github.com/aechXIII/Velo/releases"
#define AppExeName   "Velo.exe"
; Install under LocalAppData (no UAC)
#define AppInstDir   "{localappdata}\Velo"

[Setup]
AppId={{E7C3A91B-2D54-4F18-9B6E-0A1C8D4F7E22}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppSupportURL}
AppUpdatesURL={#AppUpdatesURL}
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
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AppMutex=Local\VeloSingleInstance
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
LicenseFile=..\LICENSE
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoCopyright=Copyright (c) 2026 aechXIII
CloseApplications=yes
CloseApplicationsFilter={#AppExeName}
RestartApplications=no
#ifdef SignedBuild
SignTool=velo_sign
SignedUninstaller=yes
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\Velo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\velo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\packaging\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: not IsWebView2Installed

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\velo.ico"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\velo.ico"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft Edge WebView2 Runtime..."; Flags: runhidden waituntilterminated; Check: not IsWebView2Installed
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "Velo"; Flags: uninsdeletevalue

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/f /im {#AppExeName}"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
; App install dir only - user config in %APPDATA%\Velo is kept
Type: filesandordirs; Name: "{app}"

[Code]
const
  WebView2ClientKey = 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function HasWebView2Version(RootKey: Integer): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(RootKey, WebView2ClientKey, 'pv', Version) and
    (Version <> '') and (CompareText(Version, '0.0.0.0') <> 0);
end;

function IsWebView2Installed(): Boolean;
begin
  Result := HasWebView2Version(HKCU) or HasWebView2Version(HKLM32);
end;
