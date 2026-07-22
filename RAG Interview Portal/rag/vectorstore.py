"""Vector store and retrieval setup."""

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from rag.config import CHROMA_PERSIST_DIR, COLLECTION_NAME, EMBEDDING_MODEL, RETRIEVAL_K


def get_embeddings() -> HuggingFaceEmbeddings:
    """Free local embeddings — no API key required."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def get_vector_store() -> Chroma:
    """Return a persistent Chroma vector store."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_PERSIST_DIR,
    )


def add_documents_to_store(documents: list[Document]) -> int:
    """Add document chunks to the vector store. Returns chunk count."""
    if not documents:
        return 0
    store = get_vector_store()
    store.add_documents(documents)
    return len(documents)


def get_retriever():
    """Return a retriever for RAG queries."""
    return get_vector_store().as_retriever(search_kwargs={"k": RETRIEVAL_K})


def get_collection_stats() -> dict:
    """Return basic stats about the indexed collection."""
    store = get_vector_store()
    collection = store._collection  # noqa: SLF001
    count = collection.count()
    return {"chunk_count": count, "persist_dir": CHROMA_PERSIST_DIR}
