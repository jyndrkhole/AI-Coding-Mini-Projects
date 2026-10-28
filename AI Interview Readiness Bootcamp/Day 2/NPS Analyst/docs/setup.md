# Setup

Python 3.12 and Node 22 are enough for a local run. Docker Compose is optional.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --port 8000
```

In another shell:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. The API loads `data/nps_survey.csv` and runs the specialist analysis once. Later runs with the same file and settings are reused until `force=true`.

Copy `.env.example` to `.env` if you want to change the survey path, churn assumptions, bootstrap seed, or model name. Leave `OPENAI_API_KEY` empty to stay on the deterministic path. `NPS_ENABLE_LLM=true` does not by itself send survey text anywhere; the current runtime still calculates in Python.

SQLite is created at `backend/data/nps.db` from the SQLAlchemy models when the API starts. Set `NPS_DATABASE_URL` for Postgres. The model definitions are the schema for this build.

The sample describes a fictional bank. Do not point this application at live customer data without a separate review of retention, access, and whether comments may be sent to an external model.
