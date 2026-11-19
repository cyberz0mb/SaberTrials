# One-time, read-only check of the blocked test-server executables.
# No game is launched. No ACL, ownership, antivirus or system setting is changed.
# The only write is the diagnostic report in this project's verification folder.
$ErrorActionPreference = 'Stop'
$staffRoot = Split-Path -Parent $PSScriptRoot
$staffIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$staffPrincipal = [Security.Principal.WindowsPrincipal]::new($staffIdentity)
$staffIsAdmin = $staffPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$staffChecks = @()
foreach ($staffRelative in @('dist/staff-build/Release/openjkded.x86_64.exe', 'dist/staff-build-qa/Release/openjkded.x86_64.exe')) {
    $staffFile = Join-Path $staffRoot $staffRelative
    $staffCheck = [ordered]@{file=$staffRelative; readable=$false; sha256=$null; error=$null}
    try {
        $staffCheck.sha256 = (Get-FileHash -LiteralPath $staffFile -Algorithm SHA256).Hash
        $staffCheck.readable = $true
    } catch {
        $staffCheck.error = $_.Exception.Message
    }
    $staffChecks += $staffCheck
}
$staffReport = [ordered]@{
    identity=$staffIdentity.Name
    administratorToken=$staffIsAdmin
    checks=$staffChecks
}
$staffReportDir = Join-Path $staffRoot 'dist/verification/staff-20261012'
$staffReportPath = Join-Path $staffReportDir ('admin-read-check-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
$staffReport | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $staffReportPath -Encoding UTF8
