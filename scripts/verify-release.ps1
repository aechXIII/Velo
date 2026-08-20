param(
  [string]$Version,
  [string]$Tag
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Split-Path -Parent $PSScriptRoot)).Path
Set-Location $repoRoot

if ($Tag) {
  if ($Tag -notmatch '^v\d+\.\d+\.\d+$') {
    throw "Release tag must look like vX.Y.Z: $Tag"
  }
  $tagVersion = $Tag.Substring(1)
  if ($Version -and $Version -ne $tagVersion) {
    throw "Requested version $Version does not match tag $Tag."
  }
  $Version = $tagVersion
}

function Read-Version([string]$Path, [string]$Pattern) {
  $content = Get-Content -LiteralPath $Path -Raw
  $match = [regex]::Match($content, $Pattern, [Text.RegularExpressions.RegexOptions]::Multiline)
  if (-not $match.Success) { throw "Could not read version from $Path" }
  return $match.Groups[1].Value
}

$versions = [ordered]@{
  "pyproject.toml" = Read-Version "pyproject.toml" '^version = "([^"]+)"'
  "velo/__init__.py" = Read-Version "velo\__init__.py" '^__version__ = "([^"]+)"'
  "velo/defaults.py" = Read-Version "velo\defaults.py" '^APP_VERSION = "([^"]+)"'
  "installer/Velo.iss" = Read-Version "installer\Velo.iss" '^#define AppVersion\s+"([^"]+)"'
}

$uniqueVersions = @($versions.Values | Sort-Object -Unique)
if ($uniqueVersions.Count -ne 1) {
  $detail = ($versions.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ", "
  throw "Version files disagree: $detail"
}
$actualVersion = $uniqueVersions[0]
if ($Version -and $actualVersion -ne $Version) {
  throw "Repository version $actualVersion does not match requested version $Version."
}

$changelog = Get-Content -LiteralPath "CHANGELOG.md" -Raw
if ($changelog -notmatch "(?m)^## \[$([regex]::Escape($actualVersion))\] - \d{4}-\d{2}-\d{2}\r?$") {
  throw "CHANGELOG.md has no dated section for $actualVersion."
}
if (-not (Test-Path -LiteralPath "requirements-lock.txt")) {
  throw "requirements-lock.txt is missing."
}

git diff --check
if ($LASTEXITCODE -ne 0) { throw "git diff --check failed." }

Write-Host "OK: release metadata is consistent for Velo $actualVersion" -ForegroundColor Green
