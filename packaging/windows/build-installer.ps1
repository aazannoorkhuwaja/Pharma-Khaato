$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")
python scripts/build_release.py

$iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($null -eq $iscc) {
    Write-Host "Inno Setup compiler (iscc.exe) not found. ZIP release was still created."
    exit 0
}
& $iscc.Source installer.iss
