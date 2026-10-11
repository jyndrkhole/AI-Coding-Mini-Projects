# Install Push Notifications Test Portal on Windows Server EC2.
# Run from an elevated PowerShell in the cloned project directory, or pass -AppDir.
param(
  [Parameter(Mandatory = $true)][string]$ClientId,
  [Parameter(Mandatory = $true)][string]$PublicBaseUrl,
  [Parameter(Mandatory = $true)][string]$WebhookApiKey,
  [int]$Port = 3100,
  [string]$PortalUsername = "admin",
  [string]$PortalPassword = "",
  [string]$AppDir = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
Set-Location $AppDir

if (-not $PortalPassword) {
  $bytes = New-Object byte[] 16
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  $PortalPassword = ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
  Write-Host "Generated PORTAL_PASSWORD (save this): $PortalPassword"
}

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
  "PORTAL_AUTH_ENABLED=true",
  "PORTAL_USERNAME=$PortalUsername",
  "PORTAL_PASSWORD=$PortalPassword",
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
Write-Host "Portal login: $PortalUsername / (see PORTAL_PASSWORD in .env)"
Write-Host "Health:  $base/health"
Write-Host ""
Write-Host "Start with PM2 (recommended on this EC2):"
Write-Host "  pm2 start ecosystem.config.cjs --name PushNotifications_$ClientId"
Write-Host "  pm2 save"
Write-Host "Or: npm start"
