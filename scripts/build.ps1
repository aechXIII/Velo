param(
  [Parameter(Mandatory = $false)]
  [switch]$Clean,
  [Parameter(Mandatory = $false)]
  [switch]$Installer,
  [Parameter(Mandatory = $false)]
  [switch]$Itch
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Split-Path -Parent $PSScriptRoot)).Path
Set-Location $repoRoot

function Remove-BuildDirectory([string]$Name) {
  if ($Name -notin @("build", "dist")) {
    throw "Refusing to remove unexpected directory: $Name"
  }
  $target = [IO.Path]::GetFullPath((Join-Path $repoRoot $Name))
  $expected = [IO.Path]::GetFullPath((Join-Path $repoRoot $Name))
  if ($target -ne $expected -or -not $target.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar)) {
    throw "Refusing to remove directory outside the repository: $target"
  }
  if (Test-Path -LiteralPath $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
  }
}

function Find-SignTool {
  $kits = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
  if (-not (Test-Path -LiteralPath $kits)) { return $null }
  return Get-ChildItem -LiteralPath $kits -Filter signtool.exe -Recurse -File |
    Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1 -ExpandProperty FullName
}

$signPfx = $env:VELO_SIGN_PFX
$signPassword = $env:VELO_SIGN_PASSWORD
$signTool = $null
if ($signPfx -or $signPassword) {
  if (-not $signPfx -or -not $signPassword) {
    throw "Both VELO_SIGN_PFX and VELO_SIGN_PASSWORD are required for signing."
  }
  $signPfx = (Resolve-Path -LiteralPath $signPfx).Path
  $signTool = Find-SignTool
  if (-not $signTool) { throw "signtool.exe was not found in the Windows SDK." }
}

function Invoke-CodeSign([string]$Path) {
  if (-not $signTool) { return }
  & $signTool sign /fd SHA256 /td SHA256 /tr "http://timestamp.digicert.com" /f $signPfx /p $signPassword $Path
  if ($LASTEXITCODE -ne 0) { throw "Signing failed: $Path" }
  & $signTool verify /pa $Path
  if ($LASTEXITCODE -ne 0) { throw "Signature verification failed: $Path" }
}

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
  Write-Error "Virtual environment not found. Run scripts\setup.ps1 first."
  exit 1
}

& $python -m pip install -q -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) {
  Write-Error "Could not install build dependencies."
  exit 1
}

$ico = "assets\velo.ico"
if (-not (Test-Path -LiteralPath $ico)) {
  Write-Error "Icon not found: $ico. Add assets\velo.ico before building."
  exit 1
}

if ($Clean) {
  Remove-BuildDirectory "build"
  Remove-BuildDirectory "dist"
}

& $python scripts\generate_version_info.py
if ($LASTEXITCODE -ne 0) { throw "Could not generate Windows version metadata." }
& $python scripts\collect_licenses.py
if ($LASTEXITCODE -ne 0) { throw "Could not collect third-party licenses." }

& $python -m PyInstaller --noconfirm Velo.spec
if ($LASTEXITCODE -ne 0) {
  Write-Error "PyInstaller failed."
  exit 1
}

$appExe = [IO.Path]::GetFullPath((Join-Path $repoRoot "dist\Velo\Velo.exe"))
if (-not (Test-Path -LiteralPath $appExe)) {
  Write-Error "Expected dist\Velo\Velo.exe (onedir build) missing."
  exit 1
}

foreach ($document in @("LICENSE", "PRIVACY.md", "THIRD_PARTY_NOTICES.md")) {
  Copy-Item -LiteralPath $document -Destination "dist\Velo" -Force
}
Copy-Item -LiteralPath "build\third_party_licenses" -Destination "dist\Velo\licenses" -Recurse -Force

Invoke-CodeSign $appExe

$selfTest = Start-Process -FilePath $appExe -ArgumentList "--self-test" -Wait -PassThru
if ($selfTest.ExitCode -ne 0) {
  throw "Frozen executable self-test failed with exit code $($selfTest.ExitCode)."
}
Write-Host "OK: dist\Velo\Velo.exe" -ForegroundColor Green

if ($Itch) {
  & .\scripts\stage-itch.ps1
  if ($LASTEXITCODE -ne 0) { throw "Could not stage itch build." }
  $itchSelfTest = Start-Process -FilePath "dist\Velo-itch\Velo.exe" -ArgumentList "--self-test" -Wait -PassThru
  if ($itchSelfTest.ExitCode -ne 0) {
    throw "Itch executable self-test failed with exit code $($itchSelfTest.ExitCode)."
  }
}

if ($Installer) {
  $iscc = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
  ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

  if (-not $iscc) {
    Write-Warning "Inno Setup 6 not found. Install from https://jrsoftware.org/isdl.php"
    exit 1
  }

  $webViewBootstrapper = [IO.Path]::GetFullPath(
    (Join-Path $repoRoot "packaging\MicrosoftEdgeWebview2Setup.exe")
  )
  if (-not (Test-Path -LiteralPath $webViewBootstrapper)) {
    Write-Host "Downloading the Microsoft WebView2 Evergreen Bootstrapper..." -ForegroundColor Cyan
    Invoke-WebRequest -UseBasicParsing `
      -Uri "https://go.microsoft.com/fwlink/p/?LinkId=2124703" `
      -OutFile $webViewBootstrapper
  }
  $bootstrapperSignature = Get-AuthenticodeSignature -LiteralPath $webViewBootstrapper
  if (
    $bootstrapperSignature.Status -ne "Valid" -or
    $bootstrapperSignature.SignerCertificate.Subject -notmatch "Microsoft Corporation"
  ) {
    throw "WebView2 bootstrapper does not have a valid Microsoft signature."
  }

  Write-Host "Compiling installer..." -ForegroundColor Cyan
  if ($signTool) {
    $innoSignCommand = '$q' + $signTool + '$q sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f $q' + $signPfx + '$q /p $q' + $signPassword + '$q $f'
    & $iscc "/DSignedBuild" "/Svelo_sign=$innoSignCommand" "installer\Velo.iss"
  } else {
    Write-Warning "No signing certificate configured; the build will be unsigned."
    & $iscc "installer\Velo.iss"
  }

  if ($LASTEXITCODE -ne 0) {
    Write-Error "Inno Setup failed."
    exit 1
  }

  $verLine = Select-String -Path "installer\Velo.iss" -Pattern '#define AppVersion' | Select-Object -First 1
  $ver = if ($verLine) { ($verLine.Line -replace '.*"(.+)".*','$1') } else { "unknown" }
  $installerExe = [IO.Path]::GetFullPath(
    (Join-Path $repoRoot "installer\Output\Velo-Setup-$ver.exe")
  )
  if (-not (Test-Path -LiteralPath $installerExe)) { throw "Installer output is missing." }
  if ($signTool) {
    & $signTool verify /pa /all $installerExe
    if ($LASTEXITCODE -ne 0) { throw "Installer signature verification failed." }
  }
  Write-Host "OK: installer\Output\Velo-Setup-$ver.exe" -ForegroundColor Green
}
