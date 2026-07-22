# MailMind — Local AI Email Intelligence Platform

A fully local, privacy-first AI platform for composing, rewriting, improving, and replying to business and technical emails — built for CTOs and Solution Architects.

No Gmail/Outlook integration. Your documents, style memory, and prompts stay on your machine. LLM calls go only to the provider you configure (Groq API or fully local Ollama).

---

## Features

| Area | Capability |
|------|------------|
| **Compose** | Rough notes → polished CTO-level emails |
| **Reply** | Thread-aware replies with 9 styles |
| **Thread analysis** | Summary, decisions, questions, blockers, risks, next actions |
| **Rewrite modes** | Professional, executive, shorten, expand, remove AI tone, etc. |
| **Style memory** | Learns from emails you finally send |
| **RAG knowledge base** | PDF, DOCX, TXT, MD, image OCR + ChatGPT history import |
| **Workspaces** | Isolated knowledge per customer/project |
| **Prompt library** | Built-in + custom templates |
| **Semantic search** | Query across all imported knowledge |
| **Chat** | Ask questions against your workspace KB |
| **Prompt logging** | Full input → context → prompt → response audit trail |
| **Providers** | Groq (primary) + Ollama (local) — switchable from UI |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────┐
│  React + Vite   │────▶│  FastAPI                                   │
│  Dark UI        │     │  ├─ Email / Reply / Rewrite services      │
└─────────────────┘     │  ├─ LLM factory (Groq | Ollama)           │
                        │  ├─ RAG (chunk → embed → ChromaDB)        │
                        │  ├─ Style memory + Prompt library         │
                        │  └─ SQLite (metadata) + Chroma (vectors)  │
                        └──────────────────────────────────────────┘
```

### Project layout

```
├── backend/app/
│   ├── api/routes/     # REST endpoints
│   ├── database/       # SQLAlchemy models + session
│   ├── llm/            # Provider abstraction (Groq, Ollama)
│   ├── rag/            # Chunking, embeddings, Chroma, ingest
│   ├── prompts/        # System + template prompts
│   ├── services/       # Business logic
│   └── schemas/        # Pydantic models
├── frontend/src/
│   ├── pages/          # Dashboard, Compose, Reply, KB, …
│   ├── components/     # Layout, context builder, suggestions
│   └── services/       # API client
├── vector_db/          # Chroma persistence
├── uploads/            # Ingested files
├── docker-compose.yml
└── .env
```

---

## Quick start (local)

### Prerequisites

- Python 3.11+
- Node.js 20+
- Groq API key **or** [Ollama](https://ollama.com) with a local model

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```env
GROQ_API_KEY=gsk_your_key_here
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
```

For fully local LLMs:

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3
OLLAMA_BASE_URL=http://localhost:11434
```

### 2. Start backend

```bash
chmod +x scripts/*.sh
./scripts/start-backend.sh
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Start frontend (new terminal)

```bash
./scripts/start-frontend.sh
```

UI: [http://localhost:5173](http://localhost:5173)

---

## Docker

```bash
cp .env.example .env
# set GROQ_API_KEY in .env

docker compose up --build
```

- Frontend: http://localhost:5173  
- Backend: http://localhost:8000  

---

## Recommended first-run workflow

1. **AI Settings** — confirm Groq/Ollama, set temperature & model  
2. **Workspaces** — create a workspace per customer/project  
3. **Knowledge Base** — upload architecture docs, meeting notes, SOPs, screenshots  
4. **Import ChatGPT** — paste export JSON or conversation markdown  
5. **Style Memory** — add 2–3 emails you actually sent  
6. **Compose / Reply** — select context sources, generate, edit, **Save Final + Style**

---

## API overview

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/emails/compose` | Compose from rough notes |
| `POST` | `/api/emails/reply` | Reply to a thread |
| `POST` | `/api/emails/rewrite` | One-click rewrite modes |
| `POST` | `/api/emails/analyze-thread` | Extract thread intelligence |
| `POST` | `/api/knowledge/upload` | Upload document |
| `POST` | `/api/knowledge/import-chatgpt` | Import ChatGPT history |
| `POST` | `/api/knowledge/search` | Semantic search |
| `GET/PUT` | `/api/settings` | LLM / RAG settings |
| `GET/POST` | `/api/workspaces` | Workspace management |
| `GET/POST` | `/api/prompts` | Prompt library |
| `POST` | `/api/chat` | Knowledge-aware chat |
| `GET` | `/api/logs` | Interaction logs |
| `GET` | `/api/dashboard` | Stats |

Full interactive schema: `/docs`

---

## Database schema (SQLite)

- `workspaces` — project/customer isolation  
- `documents` — uploaded/imported files + ingest status  
- `emails` — generated drafts, finals, suggestions, thread analysis  
- `style_examples` / `vocabulary_preferences` — writing style memory  
- `prompt_templates` — built-in + custom prompts  
- `interaction_logs` — full prompt audit trail  
- `app_settings` — runtime config overrides  
- `chat_messages` — workspace chat history  

Vectors live in **ChromaDB** collections named `workspace_{id}` (isolated per workspace).

---

## RAG pipeline

```
Documents → load (PDF/DOCX/TXT/MD/JSON/images)
         → RecursiveCharacterTextSplitter
         → ONNX MiniLM embeddings (local) or Ollama embeddings
         → ChromaDB (per-workspace collection)
         → Retriever (optional category filter)
         → LLM prompt context
```

ChatGPT import accepts:

- Exported conversation **JSON**  
- Plain **text / markdown** paste  
- Shared ChatGPT links are **not** supported (platform restriction) — use export/paste instead  

---

## Reply styles & rewrite modes

**Styles:** Formal, Friendly, Executive, Technical, Sales, Architecture Review, Escalation, Proposal, Follow-up  

**Rewrite:** Make Professional, Make Executive, Improve Grammar, Make More Technical, Simplify, Shorten, Expand, Add Business Justification, Add Technical Details, Improve Persuasiveness, Make Client Friendly, Remove AI Tone  

---

## Privacy

- No external email providers  
- Local SQLite + Chroma persistence  
- Optional: disable Groq and use Ollama only for air-gapped use (embeddings can also run locally)  

---

## Extending LLM providers

Implement `BaseLLMProvider` in `backend/app/llm/`, then register in `factory.py`. The UI already switches providers via settings without code deploys for Groq/Ollama.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `GROQ_API_KEY is required` | Set key in `.env` or AI Settings |
| Ollama unhealthy | `ollama serve` + `ollama pull llama3` |
| Slow first RAG ingest | Local ONNX embedding model (~80MB) downloads once into `vector_db/models/` |
| CORS errors | Ensure frontend uses Vite proxy or matching `CORS_ORIGINS` |
| Empty search results | Ingest documents into the **active** workspace |

---

## License

Personal / educational use. Adapt freely for your own productivity stack.
