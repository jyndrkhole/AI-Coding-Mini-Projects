# AWS Cost Guardian

Internal FinOps application for a read-only look at an AWS account: where money goes, what looks wasteful, and which savings ideas are safe to review first.

Phase 1 is the skeleton: FastAPI, React dashboard, SQLite, and a demo account. It does not call AWS and it does not change infrastructure.

The product specification lives in the parent `README.MD`.

## Phase 1

- Health check at `GET /api/health`
- Demo account `123456789012` (`demo-finops`, `us-east-1`)
- September 2026 demo spend of ₹18,420, previous month ₹15,870
- Estimated potential savings of ₹4,250 / month (₹51,000 / year)
- Optimization score 68 from the demo dataset
- Dashboard with cost charts and three recommendation groups
- Cost Explorer page at `/costs` with date, service, and region filters, monthly trend, service breakdown, and usage types
- `POST /api/aws/scan` reloads demo costs without calling AWS. With `MOCK_AWS=false` it reads Cost Explorer unblended cost through a profile or assumed role

Demo mode is the default (`MOCK_AWS=true`). No AWS credentials are required. Unit prices are not calculated when a rate cannot be determined (`pricing_available` is false).

## Run the API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --port 8000
```

Health: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

## Run the dashboard

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The dev server proxies `/api` to port 8000.

## Mock mode

Checked-in fixtures live in `mock_data/`. On startup the API loads them into SQLite (`backend/data/aws_cost_guardian.db`) when `MOCK_AWS=true`.

Set `MOCK_AWS=false` and the cost and account endpoints return `AWS credentials unavailable` instead of inventing numbers. Live read-only AWS access is a later phase.

Copy `.env.example` to `.env` to override settings.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Tests use a temporary database and the checked-in fixtures. They do not call AWS.

## Phases in this build

Phases 1 and 2 cover the demo dashboard and Cost Explorer. Later phases add:

- Resource inventory and CloudWatch summaries, shown at `/resources`
- Internal rules for EC2, EBS, RDS, S3, NAT, addresses, and tag coverage. Savings stay at zero unless a cost is already stored
- Compute Optimizer and Cost Optimization Hub import on a live scan, using only figures those APIs return
- An advisor at `/advisor`. It explains stored evidence. Ollama, Groq, or Bedrock is used only when that provider is configured; otherwise the answer is the stored evidence
- A business-hours what-if estimate at `/simulate`, marked ESTIMATE
- An HTML monthly report at `/report`. PDF export is not generated
- The read-only IAM policy in `infra/iam/aws-cost-guardian-readonly-policy.json`

The optimization score in demo mode is still the demo dataset value. A live account gets a score only after inventory is stored. Alembic is listed in the stack; tables are created on startup until the first migration is added.
