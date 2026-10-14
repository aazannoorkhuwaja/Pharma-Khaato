$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")

$version = python -c "from config import ApplicationSettings as A; print(A.APP_VERSION)"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($version)) {
    throw "Could not resolve Pharma Khaato version from config.py"
}
$version = $version.Trim()

python scripts/build_release.py
if ($LASTEXITCODE -ne 0) {
    throw "Native application build failed."
}

$iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($null -eq $iscc) {
    Write-Warning "Inno Setup compiler (iscc.exe) not found. The portable ZIP and checksum were created, but no Windows Setup EXE was built."
    Write-Host "Install Inno Setup and rerun this script to produce the customer installer."
    exit 0
}

& $iscc.Source "/DMyAppVersion=$version" "installer.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Windows installer compilation failed."
}

$installer = Get-ChildItem "release\Pharma-Khaato-$version-Setup-Windows-x64.exe" -ErrorAction Stop
$hash = (Get-FileHash -Algorithm SHA256 $installer.FullName).Hash.ToLowerInvariant()
Set-Content -Encoding ascii -Path ($installer.FullName + ".sha256") -Value "$hash  $($installer.Name)"
Write-Host "Windows installer: $($installer.FullName)"
Write-Host "SHA-256:          $($installer.FullName).sha256"
