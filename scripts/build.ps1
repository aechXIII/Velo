param(
  [Parameter(Mandatory = $false)]
  [switch]$Clean,
  [Parameter(Mandatory = $false)]
  [switch]$Installer
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  Write-Error "Virtual environment not found. Run scripts\setup.ps1 first."
  exit 1
}

& .\.venv\Scripts\python.exe -m pip install -q pyinstaller
if ($LASTEXITCODE -ne 0) {
  Write-Error "Could not install PyInstaller."
  exit 1
}

$ico = "assets\velo.ico"
if (-not (Test-Path $ico)) {
  Write-Error "Icon not found: $ico. Add assets\velo.ico before building."
  exit 1
}

if ($Clean) {
  if (Test-Path ".\build") { Remove-Item -Recurse -Force ".\build" }
  if (Test-Path ".\dist") { Remove-Item -Recurse -Force ".\dist" }
}

& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm Velo.spec

if ($LASTEXITCODE -ne 0) {
  Write-Error "PyInstaller failed."
  exit 1
}

Write-Host "OK: dist\Velo.exe" -ForegroundColor Green

if ($Installer) {
  $iscc = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
  ) | Where-Object { Test-Path $_ } | Select-Object -First 1

  if (-not $iscc) {
    Write-Warning "Inno Setup 6 not found. Install from https://jrsoftware.org/isdl.php"
    exit 1
  }

  Write-Host "Compiling installer..." -ForegroundColor Cyan
  & $iscc "installer\Velo.iss"

  if ($LASTEXITCODE -ne 0) {
    Write-Error "Inno Setup failed."
    exit 1
  }

  $verLine = Select-String -Path "installer\Velo.iss" -Pattern '#define AppVersion' | Select-Object -First 1
  $ver = if ($verLine) { ($verLine.Line -replace '.*"(.+)".*','$1') } else { "unknown" }
  Write-Host "OK: installer\Output\Velo-Setup-$ver.exe" -ForegroundColor Green
}
