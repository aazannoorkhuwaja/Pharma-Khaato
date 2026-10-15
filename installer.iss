; Inno Setup Script: Pharma Khaato
; Product data remains in the per-user LOCALAPPDATA directory and is not
; removed by application upgrades/uninstall unless the operator deletes it.

#define MyAppName "Pharma Khaato"
#ifndef MyAppVersion
  #define MyAppVersion "2.3.1"
#endif
#define MyAppPublisher "Pharma Khaato"
#define MyAppExeName "pharma_khaato.exe"

[Setup]
AppId={{AFC574CD-9CD5-4F3A-A209-CB3320E04F40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Pharma Khaato
DefaultGroupName=Pharma Khaato
DisableProgramGroupPage=yes
OutputDir=release
OutputBaseFilename=Pharma-Khaato-{#MyAppVersion}-Setup-Windows-x64
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Pharmacy POS & Inventory Management
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Dirs]
; Must match PathManager's stable filesystem product name under LOCALAPPDATA.
Name: "{localappdata}\Pharma-Khaato"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\data"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\logs"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\backups"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\receipts"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\exports"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\config"; Permissions: users-full

[Files]
Source: "dist\pharma_khaato\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Icons]
Name: "{autoprograms}\Pharma Khaato"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Pharma Khaato"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
