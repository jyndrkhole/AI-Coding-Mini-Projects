"""Configuration for the RAG Interview Portal."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STUDY_MATERIALS_DIR = BASE_DIR / "study_materials"
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_db"))
COLLECTION_NAME = "interview_materials"

XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip() or (
    XAI_API_KEY if XAI_API_KEY.startswith("gsk_") else ""
)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-3-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
RETRIEVAL_K = 5

SYSTEM_PROMPT = """You are an expert interview preparation coach. Answer questions using ONLY the provided study material context.

Rules:
- If the context does not contain enough information, say so clearly and suggest what topic to review.
- Structure answers for interview prep: concise definition, key points, and a short example when helpful.
- For coding/system-design topics, use bullet points and step-by-step reasoning.
- Cite which source file your answer draws from when possible.
- Be encouraging but accurate — do not invent facts beyond the context."""
