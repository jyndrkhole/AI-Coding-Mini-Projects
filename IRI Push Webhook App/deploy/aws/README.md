# AWS deploy — dedicated public host

This launches one Amazon Linux 2023 EC2 instance, builds the portal with Docker, assigns an Elastic IP, and serves it on port 80.

Use a **t3.micro** instance. That is enough for this test harness and is free-tier eligible on many accounts.

HTTPS is not included. For a test subscriber, HTTP plus `X-API-Key` is the first step. Add a domain + certificate later if you need TLS.

## What the backend will call

After the stack finishes (allow 5–8 minutes for Docker build):

```text
POST http://<elastic-ip>/webhooks/iri
Content-Type: application/json
X-API-Key: <the key you typed into CloudFormation>
```

UI: `http://<elastic-ip>`  
Health: `http://<elastic-ip>/health`

## IAM required

The CLI user `altzorAWS` currently **cannot** create EC2, images, or Lightsail instances. Launch this from the AWS **Console as an admin/root user**, or attach a policy that includes at least:

- `ec2:RunInstances`, `ec2:CreateSecurityGroup`, `ec2:AuthorizeSecurityGroupIngress`
- `ec2:CreateTags`, `ec2:AllocateAddress`, `ec2:AssociateAddress`
- `ec2:Describe*`
- `cloudformation:*`
- `ssm:GetParameters` (for the Amazon Linux AMI)

## Launch from the AWS Console

1. Sign in to the AWS account that has EC2 permission (not the limited `altzorAWS` user if it still lacks EC2).
2. Region: **US East (N. Virginia)** `us-east-1` (or change the AMI resolve if you pick another region).
3. CloudFormation → **Create stack** → **Upload a template file**.
4. Upload `deploy/aws/cloudformation.yaml`.
5. Stack name: `webhook-test-portal`.
6. **WebhookApiKey**: generate one, for example:

   ```bash
   openssl rand -hex 24
   ```

   Save it. You will not see it again in the console.
7. Create stack and wait until status is **CREATE_COMPLETE**.
8. Open the **Outputs** tab for `PortalUrl` and `WebhookUrl`.

First boot installs Docker and builds the image. `GET /health` will fail until that finishes. Then:

```bash
curl http://<elastic-ip>/health
```

## Give this curl to the backend

```bash
curl -X POST http://<elastic-ip>/webhooks/iri \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-key>" \
  -d '{
    "eventType": "applicationStatus.v1.applicationReceived",
    "policyNumber": "P987654321",
    "status": "received",
    "applicationOrigin": { "isElectronic": true }
  }'
```

## Stop billing

CloudFormation → stack `webhook-test-portal` → **Delete**. That removes the instance, Elastic IP, and security group.
