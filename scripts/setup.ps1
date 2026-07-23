param(
  [Parameter(Mandatory = $false)]
  [string]$Python = "python"
)

& $Python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (Test-Path ".\requirements-dev.txt") {
  & .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
}

Write-Host "OK: venv ready. Run .\scripts\run.ps1 or .\run.bat" -ForegroundColor Green
