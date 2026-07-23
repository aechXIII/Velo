param(
  [Parameter(Mandatory = $false)]
  [switch]$Background
)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  Write-Error "Virtual environment not found. Run scripts\setup.ps1 first."
  exit 1
}

if ($Background) {
  Start-Process -FilePath ".\.venv\Scripts\pythonw.exe" -ArgumentList "main.py" -WorkingDirectory (Get-Location)
} else {
  & .\.venv\Scripts\python.exe main.py
}
