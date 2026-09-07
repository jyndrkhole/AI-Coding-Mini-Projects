# Install Application Status Push Notifications Test Portal on Windows Server EC2.
# Run from an elevated PowerShell in the cloned project directory, or pass -AppDir.
param(
  [Parameter(Mandatory = $true)][string]$ClientId,
  [Parameter(Mandatory = $true)][string]$PublicBaseUrl,
  [Parameter(Mandatory = $true)][string]$WebhookApiKey,
  [int]$Port = 3100,
  [string]$AppDir = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
Set-Location $AppDir

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw "Node.js 20+ is required. Install LTS from https://nodejs.org then re-open PowerShell."
}

New-Item -ItemType Directory -Force -Path "data" | Out-Null

$base = $PublicBaseUrl.TrimEnd("/")
@(
  "PORT=$Port",
  "NODE_ENV=production",
  "PUBLIC_BASE_URL=$base",
  "DATABASE_PATH=./data/webhook-events.db",
  "IRI_VERSION=v1",
  "WEBHOOK_RESPONSE_STATUS=200",
  "WEBHOOK_RESPONSE_DELAY_MS=0",
  "WEBHOOK_AUTH_ENABLED=true",
  "WEBHOOK_API_KEY=$WebhookApiKey",
  "CORS_ORIGIN=*",
  "BODY_LIMIT=1mb",
  "RATE_LIMIT_WINDOW_MS=60000",
  "RATE_LIMIT_MAX=300"
) | Set-Content -Path ".env" -Encoding utf8

Write-Host "Installing npm packages..."
npm install
npm install --prefix frontend
Write-Host "Building frontend..."
npm run build --prefix frontend

$ruleName = "Webhook Portal $Port"
if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow | Out-Null
}

Write-Host ""
Write-Host "Client:  $ClientId"
Write-Host "UI:      $base"
Write-Host "Webhook: $base/webhooks/iri"
Write-Host "Health:  $base/health"
Write-Host ""
Write-Host "Start now with: npm start"
Write-Host "Then keep this window open, or install NSSM as a Windows service (see deploy/aws/README.md)."
