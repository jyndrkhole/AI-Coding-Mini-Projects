"""Local sentence-transformer embeddings. Vectors are normalized so cosine similarity is a dot product."""

from app.core.config import get_settings

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        settings = get_settings()
        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings
