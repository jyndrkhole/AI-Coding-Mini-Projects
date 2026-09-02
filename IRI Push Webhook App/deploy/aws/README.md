# Per-client AWS deploy

This portal is a **standalone webhook receiver**. Deploy **one dedicated EC2 per client**. Do not install it on a box that already runs other applications, and do not use the client’s RDS. SQLite stays on that instance.

```text
Client A  →  EC2 A  →  http://a.example.com/webhooks/iri   (API key A)
Client B  →  EC2 B  →  http://b.example.com/webhooks/iri   (API key B)
```

Each instance has its own:

- Public URL (`PUBLIC_BASE_URL`)
- `X-API-Key`
- SQLite file (Docker volume)
- Security group

Existing EC2/RDS used by other apps stay untouched.

## 1. Dedicated instance (required)

For each client, use a **separate** EC2 (or a new one). Minimum: Amazon Linux 2023, `t3.micro`, public IP or Elastic IP.

Security group on **that** instance only:

- Inbound TCP **80** (or 443 if you put nginx/TLS in front) from the backend that will POST
- SSH/SSM for you
- Do not open this on the shared app servers

Tag it, for example: `App=webhook-test-portal`, `Client=acme`.

## 2. Install on that EC2

SSH (or Session Manager) into **that client’s** instance:

```bash
sudo dnf install -y git   # if git is missing
curl -fsSL -o /tmp/install-on-ec2.sh \
  https://raw.githubusercontent.com/jyndrkhole/AI-Coding-Mini-Projects/main/IRI%20Push%20Webhook%20App/deploy/aws/install-on-ec2.sh
chmod +x /tmp/install-on-ec2.sh

sudo \
  CLIENT_ID=acme \
  PUBLIC_BASE_URL=http://203.0.113.10 \
  WEBHOOK_API_KEY="$(openssl rand -hex 24)" \
  HOST_PORT=80 \
  /tmp/install-on-ec2.sh
```

Use a **new** API key per client. Save it; the script does not print it back.

`PUBLIC_BASE_URL` is what the UI Copy URL and the backend should use (Elastic IP or DNS). No trailing slash.

Wait for the Docker build, then:

```bash
curl http://127.0.0.1/health
curl http://203.0.113.10/health
```

## 3. Give this to that client’s backend

```bash
curl -X POST http://203.0.113.10/webhooks/iri \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <client-acme-key>" \
  -d '{
    "eventType": "applicationStatus.v1.applicationReceived",
    "policyNumber": "P987654321",
    "status": "received",
    "applicationOrigin": { "isElectronic": true }
  }'
```

Repeat on the next client’s EC2 with a different `CLIENT_ID`, URL, and key.

## 4. If port 80 is already taken on a dedicated box

That usually means this is **not** a dedicated box. Prefer a new instance.

If you still terminate TLS on this host with nginx, keep the portal on 3000 and proxy:

```bash
sudo CLIENT_ID=acme PUBLIC_BASE_URL=https://webhooks-acme.example.com WEBHOOK_API_KEY=... HOST_PORT=3000 /tmp/install-on-ec2.sh
```

```nginx
server {
  listen 443 ssl;
  server_name webhooks-acme.example.com;
  location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

## 5. What not to do

- Do not deploy onto the EC2 that already hosts other client applications
- Do not create an RDS database for this app
- Do not reuse one API key across clients
- Do not point two clients at the same instance/volume

## 6. Update an existing client host

Re-run the same `install-on-ec2.sh` with the **same** `CLIENT_ID`. It pulls `main` and rebuilds. SQLite data is kept in the Docker volume `webhook-<client>_webhook-data`.

## 7. Empty-account alternative

If a client has no EC2 yet, you can still launch a new one with `deploy/aws/cloudformation.yaml` (one stack per client, different stack name and API key).
