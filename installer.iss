; Inno Setup Script: Pharma-Khaato POS
; Paths in [Dirs] intentionally mirror core/path_manager.PathManager
; (%LOCALAPPDATA%\Pharma-Khaato) so writable folders exist on first launch.

#define MyAppName "Pharma-Khaato"
#define MyAppVersion "2.3.1"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\PharmaKhaato
DefaultGroupName=Pharma-Khaato
OutputDir=dist_installer
OutputBaseFilename=PharmaKhaato_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Dirs]
; Must match PathManager._APP_NAME = "Pharma-Khaato" under LOCALAPPDATA.
Name: "{localappdata}\Pharma-Khaato"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\data"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\logs"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\backups"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\receipts"; Permissions: users-full
Name: "{localappdata}\Pharma-Khaato\exports"; Permissions: users-full

[Files]
Source: "dist\pharma_khaato\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Pharma-Khaato POS"; Filename: "{app}\pharma_khaato.exe"
Name: "{autodesktop}\Pharma-Khaato POS"; Filename: "{app}\pharma_khaato.exe"

[Run]
Filename: "{app}\pharma_khaato.exe"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
