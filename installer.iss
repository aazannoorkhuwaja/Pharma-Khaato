; Inno Setup Script: Pharma Khaato
; Product data remains in the per-user LOCALAPPDATA directory and is not
; removed by application upgrades/uninstall unless the operator deletes it.

#define MyAppName "Pharma Khaato"
#ifndef MyAppVersion
  #define MyAppVersion "2.4.1"
#endif
#define MyAppPublisher "Pharma Khaato"
#define MyAppExeName "pharma_khaato.exe"

[Setup]
AppId={{AFC574CD-9CD5-4F3A-A209-CB3320E04F40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Pharma Khaato
DefaultGroupName=Pharma Khaato
DisableProgramGroupPage=yes
OutputDir=release
OutputBaseFilename=Pharma-Khaato-{#MyAppVersion}-Setup-Windows-x64
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
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

; Shop data is created by the app for the current Windows user.
; Never grant all local users write access or delete it during uninstall.

[Files]
Source: "dist\pharma_khaato\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

Source: "packaging\windows\START-HERE.html"; DestDir: "{app}"; Flags: ignoreversion

Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Icons]
Name: "{autoprograms}\Pharma Khaato"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Pharma Khaato"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

Name: "{autoprograms}\Pharma Khaato - Getting Started"; Filename: "{app}\START-HERE.html"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
