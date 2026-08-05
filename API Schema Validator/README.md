# API Schema Validation Portal

Validate actual API responses against **OpenAPI (YAML/JSON)** or **JSON Schema** definitions.

Core validation works **without AI**. Optional LLM assistance (Ollama / Groq) is available on demand.

## Features

- Load schemas from **URL**, **file upload**, or **paste**
- Auto-detect YAML / JSON and OpenAPI vs JSON Schema
- OpenAPI path / method / status / component schema selection
- Validate required fields, types, enums, formats, additional properties, arrays, nested objects, oneOf / anyOf / allOf, `$ref`
- Monaco editors with error line highlighting
- Collapsible JSON tree + property search
- Export reports as **HTML**, **JSON**, or **PDF**
- Optional AI: Explain Errors, Suggest Fix, Generate Correct JSON, Explain Schema
- Dark & light themes

## Quick start (local)

### Backend

```bash
cd schema-validator
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # optional: configure Groq / Ollama
export PYTHONPATH=.
uvicorn backend.main:app --reload --port 8010
```

API docs: http://localhost:8010/docs

> **Note:** Default port is **8010** so it won’t collide with other local apps often bound to 8000.

### Frontend

```bash
cd schema-validator/frontend
npm install
npm run dev
```

UI: http://localhost:5174 (proxies `/api` → `http://127.0.0.1:8010`)

### Docker

```bash
cd schema-validator
docker compose up --build
```

- Frontend: http://localhost:8080  
- Backend: http://localhost:8000

## REST API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/schema/load` | Load schema (multipart: url / file / text) |
| POST | `/api/schema/validate` | Validate JSON response against schema |
| POST | `/api/schema/explain` | Optional AI assistance |
| POST | `/api/schema/export` | Export validation report |

## Privacy & security (local-only by default)

**Strict privacy mode is on by default.** Schemas and API responses stay on this machine.

| Control | Default | Effect |
|---------|---------|--------|
| `PRIVACY_MODE=strict` | on | Forces local-only boundary |
| Remote schema URL fetch | **disabled** | Use Paste / Upload only |
| Cloud LLM (Groq) | **disabled** | Prevents prompts leaving the host |
| Local LLM (Ollama) | allowed | Only `localhost` / loopback |
| Payload logging | **off** | Bodies are never written to logs |
| Core validation | local | Never calls external services |

Optional AI Assist is explicit opt-in and confirms before sending excerpts to local Ollama.

To temporarily allow remote schema fetch (not recommended for sensitive data):

```env
PRIVACY_MODE=standard
ALLOW_REMOTE_SCHEMA_FETCH=true
```

SSRF protection still blocks private/metadata IPs when URL fetch is enabled.

## Samples

| Path | Description |
|------|-------------|
| `samples/schemas/petstore.openapi.yaml` | OpenAPI 3 pet store |
| `samples/schemas/user.jsonschema.json` | JSON Schema user |
| `samples/responses/*.json` | Valid / invalid fixtures |

## Tests

```bash
cd schema-validator
source .venv/bin/activate
export PYTHONPATH=.
pytest -q
```

## Architecture

```
schema-validator/
  backend/
    api/           # FastAPI routes
    core/          # config, logging
    validators/    # JSON Schema engine + OpenAPI extractor
    services/      # load, validate, export orchestration
    llm/           # provider abstraction (Ollama / Groq)
    models/        # Pydantic contracts
  frontend/        # React + Vite + MUI + Monaco
  samples/
```

Designed for future extensions: XML, GraphQL, AsyncAPI, Protobuf, batch validation, CLI, CI plugins.
