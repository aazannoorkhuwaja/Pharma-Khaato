param([switch]$UseExistingBuild)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")

$version = python -c "from config import ApplicationSettings as A; print(A.APP_VERSION)"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($version)) {
    throw "Could not resolve Pharma Khaato version from config.py"
}
$version = $version.Trim()

# Fresh builds are the default. CI explicitly reuses its freshly verified package.
if (-not $UseExistingBuild) {
    python scripts/build_release.py
    if ($LASTEXITCODE -ne 0) {
        throw "Native application build failed."
    }
}

if (-not (Test-Path "dist\pharma_khaato\pharma_khaato.exe")) {
    throw "The packaged Windows executable is missing. Build the application first."
}
python scripts/smoke_packaged.py
if ($LASTEXITCODE -ne 0) { throw "Packaged Windows application verification failed." }

$isccPath = $null
$isccCommand = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($null -ne $isccCommand) {
    $isccPath = $isccCommand.Source
}

if ([string]::IsNullOrWhiteSpace($isccPath)) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            $isccPath = $candidate
            break
        }
    }
}

if ([string]::IsNullOrWhiteSpace($isccPath)) {
    throw "Inno Setup 6 is required to create the customer Windows Setup EXE. Install it and rerun this script."
}

New-Item -ItemType Directory -Force -Path "release" | Out-Null
& $isccPath "/DMyAppVersion=$version" "installer.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Windows installer compilation failed."
}

$installerPath = "release\Pharma-Khaato-$version-Setup-Windows-x64.exe"
$installer = Get-Item $installerPath -ErrorAction Stop
$hash = (Get-FileHash -Algorithm SHA256 $installer.FullName).Hash.ToLowerInvariant()
Set-Content -Encoding ascii -Path ($installer.FullName + ".sha256") -Value "$hash  $($installer.Name)"
Write-Host "Windows installer: $($installer.FullName)"
Write-Host "SHA-256:          $($installer.FullName).sha256"
