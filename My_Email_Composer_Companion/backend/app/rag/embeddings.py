"""Embedding providers for the RAG pipeline.

Uses Chroma's ONNX MiniLM by default (no PyTorch required).
Optionally uses Ollama embeddings when configured.
"""

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ONNX_CACHE = PROJECT_ROOT / "vector_db" / "models" / "onnx_models"


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        ...


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """ONNX all-MiniLM-L6-v2 via Chroma (lightweight, local, no torch)."""

    def __init__(self):
        self._fn = None
        self._dim: Optional[int] = None

    def _load(self):
        if self._fn is None:
            import os

            from chromadb.utils.embedding_functions import onnx_mini_lm_l6_v2 as onnx_mod

            ONNX_CACHE.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

            # Chroma hardcodes ~/.cache/chroma/onnx_models — redirect into project
            model_dir = ONNX_CACHE / "all-MiniLM-L6-v2"
            model_dir.mkdir(parents=True, exist_ok=True)
            onnx_mod.ONNXMiniLM_L6_V2.DOWNLOAD_PATH = model_dir

            self._fn = onnx_mod.ONNXMiniLM_L6_V2()
            probe = self._fn(["dimension probe"])[0]
            self._dim = len(probe)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self._load()
        assert self._fn is not None
        return self._fn(texts)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]

    @property
    def dimension(self) -> int:
        self._load()
        assert self._dim is not None
        return self._dim


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self._dim: Optional[int] = None

    async def _embed_one(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            if self._dim is None:
                self._dim = len(embedding)
            return embedding

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [await self._embed_one(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return await self._embed_one(text)

    @property
    def dimension(self) -> int:
        if self._dim is None:
            raise RuntimeError("Dimension unknown until first embedding call")
        return self._dim


@lru_cache
def get_embedding_provider() -> BaseEmbeddingProvider:
    settings = get_settings()
    if settings.embedding_provider == "ollama":
        return OllamaEmbeddingProvider(
            settings.ollama_base_url, settings.ollama_embedding_model
        )
    return LocalEmbeddingProvider()
