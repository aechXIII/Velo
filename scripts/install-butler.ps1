param(
  [string]$Version = "15.30.0",
  [string]$ExpectedSha256 = "F6D06FF12A7E1C7D4A5BD7465AA000283528E3AE2EC354448454E6FFF1F0F744",
  [string]$ArchivePath,
  [string]$Destination
)

$ErrorActionPreference = "Stop"

if ($Version -notmatch '^\d+\.\d+\.\d+$') {
  throw "Invalid Butler version: $Version"
}
if ($ExpectedSha256 -notmatch '^[0-9a-fA-F]{64}$') {
  throw "ExpectedSha256 must be a 64-character hexadecimal SHA-256 digest."
}

$temporaryRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [IO.Path]::GetTempPath() }
if ([string]::IsNullOrWhiteSpace($Destination)) {
  $Destination = Join-Path $temporaryRoot "butler-$Version"
}
$destinationPath = [IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $destinationPath) {
  throw "Butler destination already exists: $destinationPath"
}

$downloadedArchive = $false
if ([string]::IsNullOrWhiteSpace($ArchivePath)) {
  $ArchivePath = Join-Path $temporaryRoot "butler-$Version-$([guid]::NewGuid().ToString('N')).zip"
  $url = "https://broth.itch.zone/butler/windows-amd64/$Version/archive/default"
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $ArchivePath
  $downloadedArchive = $true
} elseif (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
  throw "Butler archive not found: $ArchivePath"
}

$archiveFullPath = [IO.Path]::GetFullPath($ArchivePath)
try {
  $stream = [IO.File]::OpenRead($archiveFullPath)
  $sha256 = [Security.Cryptography.SHA256]::Create()
  try {
    $actualSha256 = [BitConverter]::ToString($sha256.ComputeHash($stream)).Replace("-", "")
  } finally {
    $sha256.Dispose()
    $stream.Dispose()
  }
  if ($actualSha256 -ne $ExpectedSha256) {
    throw "Butler archive SHA-256 mismatch. Expected $ExpectedSha256, got $actualSha256."
  }

  New-Item -ItemType Directory -Path $destinationPath | Out-Null
  Expand-Archive -LiteralPath $archiveFullPath -DestinationPath $destinationPath
  if (-not (Test-Path -LiteralPath (Join-Path $destinationPath "butler.exe") -PathType Leaf)) {
    throw "Verified Butler archive does not contain butler.exe."
  }

  Write-Output $destinationPath
} finally {
  if ($downloadedArchive -and (Test-Path -LiteralPath $archiveFullPath)) {
    Remove-Item -LiteralPath $archiveFullPath -Force
  }
}
