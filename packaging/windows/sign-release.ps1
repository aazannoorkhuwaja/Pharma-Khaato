param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($env:WINDOWS_CERT_BASE64) -or [string]::IsNullOrWhiteSpace($env:WINDOWS_CERT_PASSWORD)) {
    throw 'Both Windows signing secrets are required when signing is enabled.'
}
$executable = (Resolve-Path $Target).Path
$certificatePath = Join-Path $env:RUNNER_TEMP ('pharma-sign-' + [guid]::NewGuid().ToString('N') + '.pfx')
try {
    [IO.File]::WriteAllBytes($certificatePath, [Convert]::FromBase64String($env:WINDOWS_CERT_BASE64))
    $tools = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" | Sort-Object FullName -Descending
    if (-not $tools) { throw 'Windows SDK signtool.exe was not found.' }
    $signTool = $tools[0].FullName
    & $signTool sign /fd SHA256 /f $certificatePath /p $env:WINDOWS_CERT_PASSWORD /tr http://timestamp.digicert.com /td SHA256 $executable
    if ($LASTEXITCODE -ne 0) { throw 'Windows signing failed.' }
    $signature = Get-AuthenticodeSignature $executable
    if ($signature.Status -ne 'Valid' -or $null -eq $signature.TimeStamperCertificate) {
        throw 'The Windows signature or timestamp did not validate.'
    }
    # Signing changes bytes; regenerate an existing checksum only afterwards.
    if (Test-Path ($executable + '.sha256')) {
        $hash = (Get-FileHash $executable -Algorithm SHA256).Hash.ToLowerInvariant()
        Set-Content -Encoding ascii ($executable + '.sha256') "$hash  $([IO.Path]::GetFileName($executable))"
    }
} finally {
    Remove-Item $certificatePath -Force -ErrorAction SilentlyContinue
}
