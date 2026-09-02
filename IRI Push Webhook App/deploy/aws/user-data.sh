#!/bin/bash
set -euxo pipefail

dnf update -y
dnf install -y docker git
systemctl enable --now docker

if ! docker compose version >/dev/null 2>&1; then
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -fsSL "https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-x86_64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

TOKEN=$(curl -fsS -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
PUBLIC_IP=$(curl -fsS -H "X-aws-ec2-metadata-token: ${TOKEN}" \
  http://169.254.169.254/latest/meta-data/public-ipv4)

install -d /opt/webhook-portal
cd /opt/webhook-portal
if [ ! -d repo/.git ]; then
  git clone --depth 1 https://github.com/jyndrkhole/AI-Coding-Mini-Projects.git repo
fi
cd "repo/IRI Push Webhook App"
git fetch --depth 1 origin main
git checkout -f origin/main

sed -i '/PUBLIC_BASE_URL:/d' docker-compose.yml || true

cat > .env <<EOF
PORT=3000
NODE_ENV=production
PUBLIC_BASE_URL=http://${PUBLIC_IP}
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
HOST_PORT=80
EOF

cat > docker-compose.override.yml <<'EOF'
services:
  portal:
    ports:
      - "80:3000"
    restart: unless-stopped
EOF

docker compose up -d --build
