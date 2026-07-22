# RAG Interview Portal

A personal interview-prep portal that answers questions from **your own study material** using RAG (Retrieval-Augmented Generation).

## Stack (mostly free)

| Component | Tool | Cost |
|-----------|------|------|
| UI | **Gradio** | Free |
| Orchestration | **LangChain** | Free |
| LLM | **Grok (xAI)** | Free tier / low cost |
| Embeddings | **sentence-transformers** (local) | Free |
| Vector DB | **ChromaDB** (local) | Free |

## How it works

```
Study PDFs/notes → chunk → embed locally → store in ChromaDB
                                              ↓
Your question → retrieve top chunks → Grok generates answer + sources
```

## Quick start

### 1. Setup

```bash
cd "RAG Interview Portal"
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your Grok API key

```bash
cp .env.example .env
# Edit .env and set XAI_API_KEY=your_key
```

Get a key at [console.x.ai](https://console.x.ai/).

### 3. Add study material

Either:
- Put files in `study_materials/` (PDF, TXT, MD), or
- Upload via the Gradio UI

### 4. Run

```bash
python app.py
```

Open the local URL (usually `http://127.0.0.1:7860`).

### 5. Use

1. Go to **Upload & Index** → index your files
2. Go to **Chat** → ask interview questions
3. Check **Retrieved sources** panel for citations

## Supported file types

- `.pdf` — interview PDFs, notes
- `.txt` — plain text notes
- `.md` — markdown study guides

## Project structure

```
├── app.py              # Gradio UI
├── rag/
│   ├── config.py       # Settings & prompts
│   ├── ingest.py       # Load & chunk documents
│   ├── vectorstore.py  # ChromaDB + embeddings
│   └── chain.py        # RAG chain with Grok
├── study_materials/    # Drop your files here
├── chroma_db/          # Local vector store (auto-created)
└── requirements.txt
```

## Tips for better results

1. **Organize by topic** — e.g. `dsa.pdf`, `system-design.md`, `sql-notes.txt`
2. **Re-index after adding files** — each upload appends to the store
3. **Ask specific questions** — "Explain MVCC in PostgreSQL" beats "tell me about databases"
4. **Tune chunk size** in `rag/config.py` if answers miss context

## Optional upgrades

- Add `.docx` support (already in requirements, extend `ingest.py`)
- Use **Ollama** instead of Grok for fully offline LLM
- Add quiz mode: Grok generates questions from your material
- Deploy with `gradio deploy` or Docker for access from phone

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `XAI_API_KEY is not set` | Create `.env` from `.env.example` |
| Slow first run | sentence-transformers downloads the model once (~80MB) |
| Empty answers | Index files first; check **Status** tab for chunk count |
| PDF errors | Ensure PDF is text-based, not scanned images |


flowchart LR
    A[Local HTML files] --> B[Extract text]
    C[URLs in urls.txt / .md] --> D[Fetch page content]
    E[PDF / TXT / MD] --> B
    B --> F[Chunk + embed]
    D --> F
    F --> G[(ChromaDB)]
    H[Your question] --> I[Retrieve chunks]
    I --> G
    I --> J[Groq LLM]
