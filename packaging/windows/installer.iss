#define MyAppName "Karst Rainfall-Response Analysis"
#define MyAppVersion "0.1.0"
#define MyAppExeName "Karst Rainfall-Response Analysis.exe"

[Setup]
AppId={{9D2605F4-1D36-42CE-A2DA-21D7D5E6C5A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\..\dist\installer
OutputBaseFilename=setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=no
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{userappdata}\{#MyAppName}\logs"
Name: "{userappdata}\{#MyAppName}\matplotlib"
Name: "{userdocs}\{#MyAppName}\outputs"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
