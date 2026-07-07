param(
  [string]$ApiUrl = "http://localhost:9000",
  [int]$Port = 3000
)

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\frontend"

$env:API_URL = $ApiUrl

if (-not (Test-Path "node_modules")) {
  corepack yarn install --frozen-lockfile
}

corepack yarn run dev --no-fork --host 0.0.0.0 --port $Port
