"""Application configuration loaded from environment."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

FREE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]

ECOMMERCE_PLATFORMS = [
    "Amazon",
    "Flipkart",
    "Croma",
    "Reliance Digital",
    "Vijay Sales",
    "Tata CLiQ",
    "Myntra",
    "Ajio",
    "Nykaa",
    "Meesho",
    "Snapdeal",
    "Pepperfry",
]

# Editorial / recommendation sites used for reviews & buying guides
RECOMMENDATION_SITES = [
    "NDTV Shopping",
    "Hindustan Times",
    "Gadgets 360",
    "91mobiles",
    "Smartprix",
    "Digit",
    "India Today Tech",
]

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 7860
