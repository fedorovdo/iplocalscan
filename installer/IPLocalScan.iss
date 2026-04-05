#define MyAppName "IP Local Scan"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Dmitrii Fedorov"
#define MyAppURL "https://github.com/fedorovdo/iplocalscan"
#define MyAppExeName "iplocalscan.exe"

[Setup]
AppId={{C6D3B0F0-6E0B-4B87-9D7A-6A1F4F7E4D21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\IP Local Scan
DefaultGroupName=IP Local Scan
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=IPLocalScan_v{#MyAppVersion}_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\iplocalscan\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\IP Local Scan"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\IP Local Scan"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch IP Local Scan"; Flags: nowait postinstall skipifsilent