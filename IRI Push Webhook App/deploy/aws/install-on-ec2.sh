#!/bin/bash
# Install or update the Webhook Test Portal on THIS EC2.
# Run once per client on that client's dedicated instance. Do not share the box
# with other applications, and do not point this app at RDS — it uses local SQLite.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root (sudo)."
  exit 1
fi

CLIENT_ID="${CLIENT_ID:?Set CLIENT_ID to a short client slug, e.g. acme}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:?Set PUBLIC_BASE_URL, e.g. http://203.0.113.10}"
WEBHOOK_API_KEY="${WEBHOOK_API_KEY:?Set WEBHOOK_API_KEY}"
HOST_PORT="${HOST_PORT:-80}"
REPO_URL="${REPO_URL:-https://github.com/jyndrkhole/AI-Coding-Mini-Projects.git}"
APP_SUBDIR="${APP_SUBDIR:-IRI Push Webhook App}"

INSTALL_ROOT="/opt/webhook-portal/${CLIENT_ID}"
COMPOSE_PROJECT="webhook-${CLIENT_ID}"

if command -v dnf >/dev/null 2>&1; then
  dnf install -y docker git
elif command -v yum >/dev/null 2>&1; then
  yum install -y docker git
elif command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y docker.io git
else
  echo "Install Docker and git, then re-run."
  exit 1
fi

systemctl enable --now docker || true

if ! docker compose version >/dev/null 2>&1; then
  mkdir -p /usr/local/lib/docker/cli-plugins
  ARCH="$(uname -m)"
  case "$ARCH" in
    aarch64|arm64) COMPOSE_ARCH="aarch64" ;;
    *) COMPOSE_ARCH="x86_64" ;;
  esac
  curl -fsSL "https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-${COMPOSE_ARCH}" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

mkdir -p "$INSTALL_ROOT"
cd "$INSTALL_ROOT"
if [ ! -d repo/.git ]; then
  git clone --depth 1 "$REPO_URL" repo
else
  git -C repo fetch --depth 1 origin main
  git -C repo checkout -f origin/main
fi

APP_DIR="${INSTALL_ROOT}/repo/${APP_SUBDIR}"
cd "$APP_DIR"
sed -i '/PUBLIC_BASE_URL:/d' docker-compose.yml || true

cat > .env <<EOF
PORT=3000
NODE_ENV=production
PUBLIC_BASE_URL=${PUBLIC_BASE_URL%/}
DATABASE_PATH=/app/data/webhook-events.db
IRI_VERSION=v1
WEBHOOK_RESPONSE_STATUS=200
WEBHOOK_RESPONSE_DELAY_MS=0
WEBHOOK_AUTH_ENABLED=true
WEBHOOK_API_KEY=${WEBHOOK_API_KEY}
CORS_ORIGIN=*
BODY_LIMIT=1mb
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX=300
HOST_PORT=${HOST_PORT}
EOF

COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT" HOST_PORT="$HOST_PORT" docker compose up -d --build

echo
echo "Client:     ${CLIENT_ID}"
echo "UI:         ${PUBLIC_BASE_URL%/}"
echo "Webhook:    ${PUBLIC_BASE_URL%/}/webhooks/iri"
echo "Health:     ${PUBLIC_BASE_URL%/}/health"
echo "Header:     X-API-Key: (the WEBHOOK_API_KEY you passed)"
echo "Data:       Docker volume ${COMPOSE_PROJECT}_webhook-data (SQLite, not RDS)"
echo
echo "Open security group TCP ${HOST_PORT} to the backend that will POST."
