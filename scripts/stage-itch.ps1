param(
  [string]$Source = "dist\Velo",
  [string]$Target = "dist\Velo-itch"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Split-Path -Parent $PSScriptRoot)).Path
Set-Location $repoRoot

$sourcePath = [IO.Path]::GetFullPath((Join-Path $repoRoot $Source))
$targetPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $Target))
$distRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot "dist"))
$expectedTarget = [IO.Path]::GetFullPath((Join-Path $distRoot "Velo-itch"))

if (-not (Test-Path -LiteralPath $sourcePath -PathType Container)) {
  throw "Build directory not found: $sourcePath"
}
if ($targetPath -ne $expectedTarget) {
  throw "Refusing to replace unexpected itch staging directory: $targetPath"
}
if ($targetPath -eq $sourcePath) {
  throw "Source and target directories must differ."
}

if (Test-Path -LiteralPath $targetPath) {
  Remove-Item -LiteralPath $targetPath -Recurse -Force
}
New-Item -ItemType Directory -Path $targetPath | Out-Null
Copy-Item -Path (Join-Path $sourcePath "*") -Destination $targetPath -Recurse -Force
Copy-Item -LiteralPath "packaging\itch\.itch.toml" -Destination $targetPath -Force
Copy-Item -LiteralPath "packaging\itch\distribution.json" -Destination $targetPath -Force

Write-Host "OK: staged itch build at $targetPath" -ForegroundColor Green
