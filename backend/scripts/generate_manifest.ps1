$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$backend = Join-Path $root "backend"
$manifestPath = Join-Path $backend "release_manifest.json"

function Get-RelPath($path, $base) {
  $uri1 = New-Object System.Uri(($base + [IO.Path]::DirectorySeparatorChar))
  $uri2 = New-Object System.Uri($path)
  return $uri1.MakeRelativeUri($uri2).ToString().Replace("\", "/")
}

$artifacts = @()
Get-ChildItem -Path $backend -Recurse -File | ForEach-Object {
  if ($_.FullName -match "__pycache__|\.pytest_cache") { return }
  $hash = (Get-FileHash -Algorithm SHA256 -Path $_.FullName).Hash.ToLower()
  $rel = Get-RelPath $_.FullName $root.Path
  $artifacts += @{
    path = $rel
    sha256 = $hash
    bytes = $_.Length
  }
}

$manifest = @{
  release_branch = "release/backend-next"
  generated_from = $root.Path
  artifacts = $artifacts
  tests = @{
    unit_pytest = $(if ([string]::IsNullOrEmpty($env:MANIFEST_PYTEST_STATUS)) { "unknown" } else { $env:MANIFEST_PYTEST_STATUS })
    e2e_smoke = $(if ([string]::IsNullOrEmpty($env:MANIFEST_E2E_STATUS)) { "unknown" } else { $env:MANIFEST_E2E_STATUS })
  }
  notes = @(
    "If CI ran, set MANIFEST_PYTEST_STATUS and MANIFEST_E2E_STATUS env vars before generating."
  )
}

$json = $manifest | ConvertTo-Json -Depth 6
Set-Content -Path $manifestPath -Value $json -Encoding UTF8
Write-Host "Wrote $manifestPath"

