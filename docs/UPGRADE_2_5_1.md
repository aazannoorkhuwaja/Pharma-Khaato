# Upgrade from 2.5.0 to 2.5.1

Download the installer for your platform and its matching .sha256 file from the [official release](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/tag/v2.5.1). Save both in the same folder.

Use a practice system. If the existing installation holds shop records, verify a recent backup by restoring it on a separate test machine first. If the installed version reports that backup verification failed, stop before upgrading that shop. Finish any pending checkout, close all counters and exit the app before running the installer.

**Windows 10/11 x64.** In the folder containing Setup and its checksum, run PowerShell:

```powershell
$file = 'Pharma-Khaato-2.5.1-Setup-Windows-x64.exe'
$expected = ((Get-Content "$file.sha256" -Raw).Trim() -split '\s+')[0]
if ((Get-FileHash $file -Algorithm SHA256).Hash -ne $expected) { throw 'Checksum mismatch' }
Start-Process -Wait -FilePath ".\$file"
```

Keep the existing installation location. This Windows build is unsigned and requires manual installation. If Windows or your shop policy requires a trusted signature, use the signed release when available.

**Ubuntu amd64.** Open a terminal in the folder containing the Debian package and checksum:

```bash
sha256sum -c Pharma-Khaato-2.5.1-linux-amd64.deb.sha256 &&
  sudo apt install ./Pharma-Khaato-2.5.1-linux-amd64.deb
```

Launch from Start on Windows or run `pharma-khaato` on Ubuntu. Under the same operating-system account, open **About Pharma Khaato** and confirm **2.5.1**. Check that your practice shop, recent receipt, stock and customer dues are present, then create and verify a new backup.
