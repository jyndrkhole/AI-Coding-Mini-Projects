# Per-client AWS deploy (same EC2 as other apps)

Install this portal on **that client’s existing EC2**, on a **free port**. Other apps keep their ports. Webhook data stays on that machine as SQLite (not RDS).

```text
Client A EC2
  :443  existing app
  :8080 existing API
  :3100 this webhook portal  ← only this client's POSTs

Client B EC2
  :443  existing app
  :3100 this webhook portal  ← only B's POSTs
```

Isolation is **per EC2 + per API key**, not a shared multi-tenant server.

## 1. Pick a free port

On the client EC2:

```bash
ss -lnt
```

Choose a port nothing else uses. **3100** is the default in the install script. Do not bind 80/443 if nginx or another app already owns them.

Security group on **this** instance: inbound TCP **3100** (or your chosen port) from the backend that will POST.

## 2. Install alongside the other apps

SSH into that client’s EC2:

```bash
curl -fsSL -o /tmp/install-on-ec2.sh \
  https://raw.githubusercontent.com/jyndrkhole/AI-Coding-Mini-Projects/main/IRI%20Push%20Webhook%20App/deploy/aws/install-on-ec2.sh
chmod +x /tmp/install-on-ec2.sh

sudo \
  CLIENT_ID=acme \
  HOST_PORT=3100 \
  PUBLIC_BASE_URL=http://<this-ec2-public-ip>:3100 \
  WEBHOOK_API_KEY="$(openssl rand -hex 24)" \
  /tmp/install-on-ec2.sh
```

Include **`:3100`** in `PUBLIC_BASE_URL` so the UI Copy URL matches what the backend calls.

Save the API key. Generate a different key on the next client’s EC2.

Wait for the Docker build, then:

```bash
curl http://127.0.0.1:3100/health
curl http://<this-ec2-public-ip>:3100/health
```

The container name/volume is `webhook-acme`, so it will not reuse another Docker project’s volumes.

## 3. Give this to that client’s backend

```bash
curl -X POST http://<this-ec2-public-ip>:3100/webhooks/iri \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <client-acme-key>" \
  -d '{
    "eventType": "applicationStatus.v1.applicationReceived",
    "policyNumber": "P987654321",
    "status": "received",
    "applicationOrigin": { "isElectronic": true }
  }'
```

That traffic lands only on this EC2. Repeat on the next client host with a different IP, port (if needed), `CLIENT_ID`, and key.

## 4. Optional: HTTPS via existing nginx

If this EC2 already terminates TLS, keep `HOST_PORT=3100` and proxy a hostname:

```nginx
server {
  listen 443 ssl;
  server_name webhooks-acme.example.com;
  location / {
    proxy_pass http://127.0.0.1:3100;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

Then set `PUBLIC_BASE_URL=https://webhooks-acme.example.com` (no port). You do not need to open 3100 publicly if only nginx talks to it.

## 5. What not to do

- Do not use RDS for this app (SQLite stays in Docker volume `webhook-<client>_webhook-data`)
- Do not reuse one API key across clients
- Do not run two clients’ portals on the same EC2 (that would mix their webhook logs)
- Do not bind a port already used by another process

## 6. Update

Re-run the same script with the **same** `CLIENT_ID` and `HOST_PORT`. It pulls `main` and rebuilds; existing events stay on the volume.

## 7. Windows Server EC2

Do not use `install-on-ec2.sh` on Windows. Use Node.js on a free port (default **3100**).

### Prerequisites

- Node.js 22 LTS (https://nodejs.org)
- Git clone of this repo
- Inbound TCP **3100** on the instance security group
- If `npm install` fails on `better-sqlite3`, install Visual Studio Build Tools (Desktop development with C++)

### Commands (Administrator PowerShell)

```powershell
cd C:\path\to\IRIPushWebhook

netstat -ano | findstr ":3100"

copy .env.example .env
notepad .env
```

Set in `.env`:

```env
PORT=3100
NODE_ENV=production
PUBLIC_BASE_URL=http://<EC2_PUBLIC_IP>:3100
DATABASE_PATH=./data/webhook-events.db
WEBHOOK_AUTH_ENABLED=true
WEBHOOK_API_KEY=<generate-and-save>
```

Or run the helper (writes `.env`, installs, builds, opens the firewall):

```powershell
cd C:\path\to\IRIPushWebhook
powershell -ExecutionPolicy Bypass -File .\deploy\aws\install-on-windows.ps1 `
  -ClientId acme `
  -PublicBaseUrl http://<EC2_PUBLIC_IP>:3100 `
  -WebhookApiKey "<API_KEY>" `
  -Port 3100
```

Then:

```powershell
New-Item -ItemType Directory -Force -Path data
npm install
npm install --prefix frontend
npm run build --prefix frontend
New-NetFirewallRule -DisplayName "Webhook Portal 3100" -Direction Inbound -Protocol TCP -LocalPort 3100 -Action Allow
npm start
```

Health: `http://127.0.0.1:3100/health`  
UI: `https://client-pushconsole.abc.com` (or `http://127.0.0.1:3100`)  
Webhook: `POST https://client-pushconsole.abc.com/webhooks/iri` with `X-API-Key`

### Run with PM2 (same as the other apps on this EC2)

Do **not** leave `npm start` in an RDP window. Add this portal as one more PM2 process, on a **free** port (default **3100**). Leave the existing AgentVizion / API processes alone.

```powershell
cd C:\path\to\IRIPushWebhook

# stop a leftover console npm start if it is still bound to 3100
netstat -ano | findstr ":3100"

git pull
npm run build --prefix frontend

notepad .env
```

Set `PORT=3100` and `PUBLIC_BASE_URL=https://client-pushconsole.abc.com` (your real hostname).

Name it like the other apps (`App_Client_Env`):

```powershell
pm2 start ecosystem.config.cjs --name PushNotifications_GAFG_Staging
pm2 save
pm2 status
```

`ecosystem.config.cjs` uses **fork** mode (same as your other Windows processes). `.env` is loaded by the app.

Useful commands:

```powershell
pm2 restart PushNotifications_GAFG_Staging
pm2 logs PushNotifications_GAFG_Staging
pm2 stop PushNotifications_GAFG_Staging
```

After a code pull:

```powershell
git pull
npm run build --prefix frontend
pm2 restart PushNotifications_GAFG_Staging
```

If `https://client-pushconsole.abc.com` is served by `reverse_proxy_server` (or IIS), proxy `/` to `http://127.0.0.1:3100` and send `Host` plus `X-Forwarded-Proto: https`. That PM2 process is currently **stopped** in your list — start it only if that is how TLS/hostname routing is done.

To survive reboot, keep using the same PM2 Windows startup you already use for the other apps (`pm2 save`). NSSM is not needed if PM2 is already the process manager.

### Pull this Windows update on the EC2

```powershell
cd C:\path\to\IRIPushWebhook
git pull
```

