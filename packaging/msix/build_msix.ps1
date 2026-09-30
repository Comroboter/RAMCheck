<#
  Builds the Microsoft Store package (MSIX) of RAMCheck.

  Usage (PowerShell, in the RAMCheck folder):
    .\packaging\msix\build_msix.ps1 -IdentityName "12345Comroboter.RAMCheck" `
        -Publisher "CN=ABCD1234-...." -PublisherDisplayName "Comroboter"

  The three values come from Partner Center > your app > Product management > Product identity.
  The result is dist\RAMCheck-Store.msix, which you upload in Partner Center. It doesn't need to be
  signed: the Store signs it. Add -TestSign to also create a self-signed copy you can install
  locally for testing (see the tutorial in packaging\store\STORE_GUIDE.md).
#>
param(
  [Parameter(Mandatory = $true)][string]$IdentityName,
  [Parameter(Mandatory = $true)][string]$Publisher,
  [Parameter(Mandatory = $true)][string]$PublisherDisplayName,
  [switch]$TestSign
)
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location $root

# 1. the app itself (the same folder build the installer uses)
if (-not (Test-Path "dist\RAMCheck\RAMCheck.exe")) {
  Write-Host "dist\RAMCheck not found, running build.bat first ..."
  $env:CI = "true"
  cmd /c build.bat
  if ($LASTEXITCODE -ne 0) { throw "build.bat failed" }
}

# 2. find makeappx.exe from the Windows SDK
$sdk = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\makeappx.exe" -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending | Select-Object -First 1
if (-not $sdk) {
  throw "makeappx.exe not found. Install the Windows SDK:  winget install Microsoft.WindowsSDK.10.0.26100"
}

# 3. package layout: app files + icons + manifest
$version = (python tools\build_helpers.py msix-version).Trim()
$layout = "build\msix-layout"
if (Test-Path $layout) { Remove-Item $layout -Recurse -Force }
New-Item -ItemType Directory $layout | Out-Null
Copy-Item "dist\RAMCheck\*" $layout -Recurse
Copy-Item "packaging\msix\Assets" "$layout\Assets" -Recurse
Remove-Item "$layout\Assets\Store300x300.png" -ErrorAction SilentlyContinue
$manifest = Get-Content "packaging\msix\AppxManifest.xml" -Raw
$manifest = $manifest.Replace("{{IdentityName}}", $IdentityName).Replace("{{Publisher}}", $Publisher)
$manifest = $manifest.Replace("{{PublisherDisplayName}}", $PublisherDisplayName).Replace("{{Version}}", $version)
Set-Content "$layout\AppxManifest.xml" $manifest -Encoding UTF8

# 4. pack
New-Item -ItemType Directory dist -Force | Out-Null
$out = "dist\RAMCheck-Store.msix"
& $sdk.FullName pack /d $layout /p $out /o
if ($LASTEXITCODE -ne 0) { throw "makeappx failed" }
Write-Host "Store package: $out (version $version)"

# 5. optional: a self-signed copy for installing it on this PC before submitting
if ($TestSign) {
  $signtool = Join-Path $sdk.DirectoryName "signtool.exe"
  $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $Publisher } | Select-Object -First 1
  if (-not $cert) {
    $cert = New-SelfSignedCertificate -Type Custom -Subject $Publisher -KeyUsage DigitalSignature `
      -FriendlyName "RAMCheck test signing" -CertStoreLocation "Cert:\CurrentUser\My" `
      -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
  }
  Export-Certificate -Cert $cert -FilePath "dist\RAMCheck-TestCert.cer" | Out-Null
  $test = "dist\RAMCheck-Store-TestSigned.msix"
  Copy-Item $out $test -Force
  & $signtool sign /fd SHA256 /sha1 $cert.Thumbprint $test
  if ($LASTEXITCODE -ne 0) { throw "signtool failed" }
  Write-Host "Test package: $test"
  Write-Host "Trust the test certificate once (as admin):"
  Write-Host "  Import-Certificate -FilePath dist\RAMCheck-TestCert.cer -CertStoreLocation Cert:\LocalMachine\TrustedPeople"
}
