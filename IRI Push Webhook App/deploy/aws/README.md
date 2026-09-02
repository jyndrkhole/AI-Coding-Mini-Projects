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
