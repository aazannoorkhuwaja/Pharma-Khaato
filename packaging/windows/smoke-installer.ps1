# Run only on an isolated Windows test machine/CI runner, never a live counter.
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")
$version = (python -c "from config import ApplicationSettings as A; print(A.APP_VERSION)").Trim()
if ($LASTEXITCODE -ne 0) { throw "Cannot read application version." }
$setup = (Resolve-Path "release\Pharma-Khaato-$version-Setup-Windows-x64.exe").Path
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("Pharma Windows Check " + [guid]::NewGuid().ToString('N'))
$installDir = Join-Path $testRoot "Installed App"
$dataDir = Join-Path $testRoot "Shop Data"
New-Item -ItemType Directory -Force $dataDir | Out-Null
$oldDataDir = $env:PHARMA_KHAATO_DATA_DIR

function Invoke-CheckedProcess([string]$Executable, [string[]]$Arguments) {
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -PassThru
    $null = $process.Handle
    if (-not $process.WaitForExit(180000)) {
        $process.Kill()
        throw "Windows verification timed out: $Executable"
    }
    if ($process.ExitCode -ne 0) { throw "Process failed ($($process.ExitCode)): $Executable" }
}

try {
    $env:PHARMA_KHAATO_DATA_DIR = $dataDir
    $setupArguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', "/DIR=`"$installDir`"")
    Invoke-CheckedProcess $setup $setupArguments
    $exe = Join-Path $installDir 'pharma_khaato.exe'
    if (-not (Test-Path $exe)) { throw "Setup did not install the application." }
    if (-not (Test-Path (Join-Path $installDir 'START-HERE.html'))) { throw "Getting-started guide missing." }

    python scripts/smoke_packaged.py --executable $exe
    if ($LASTEXITCODE -ne 0) { throw "Installed application functional check failed." }
    # Create a real migrated database outside the install folder.
    Invoke-CheckedProcess $exe @('--self-check', '--headless')
    $database = Join-Path $dataDir 'data\pharmacy_db.sqlite'
    if (-not (Test-Path $database)) { throw "Installed app did not initialise its data folder." }
    # Persist synthetic shop content as well as the migrated schema.
    python -c "import os,sqlite3; from pathlib import Path; db=sqlite3.connect(Path(os.environ['PHARMA_KHAATO_DATA_DIR'])/'data'/'pharmacy_db.sqlite'); db.execute('INSERT INTO Pharmacy_Settings(setting_key,setting_value) VALUES(?,?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value', ('pharmacy_name','Windows retention test')); db.commit(); db.close()"
    if ($LASTEXITCODE -ne 0) { throw "Cannot prepare test shop content." }
    $beforeHash = (Get-FileHash $database -Algorithm SHA256).Hash
    $marker = Join-Path $dataDir 'keep-my-shop-records.txt'
    Set-Content $marker 'Shop data must survive reinstall and uninstall.'

    Invoke-CheckedProcess $setup $setupArguments
    if ((Get-FileHash $database -Algorithm SHA256).Hash -ne $beforeHash) { throw "Reinstall changed the shop database." }
    python scripts/smoke_packaged.py --executable $exe
    if ($LASTEXITCODE -ne 0) { throw "Reinstalled application functional check failed." }

    $uninstaller = Join-Path $installDir 'unins000.exe'
    Invoke-CheckedProcess $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "_?=`"$installDir`"")
    if (Test-Path $exe) { throw "Uninstall left the application executable behind." }
    if (-not (Test-Path $marker)) { throw "Uninstall removed the shop data marker." }
    if ((Get-FileHash $database -Algorithm SHA256).Hash -ne $beforeHash) { throw "Uninstall changed the shop database." }
    Write-Host 'PASS: Windows install, installed functional check, reinstall and database retention after uninstall.'
} finally {
    $env:PHARMA_KHAATO_DATA_DIR = $oldDataDir
    # On failure retain the isolated directory for investigation.
    Write-Host "Isolated Windows test evidence: $testRoot"
}
