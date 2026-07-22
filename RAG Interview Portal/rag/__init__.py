"""RAG Interview Portal — public API."""

from rag.chain import ask, build_rag_chain
from rag.config import STUDY_MATERIALS_DIR
from rag.ingest import (
    load_documents_from_folder,
    load_documents_from_paths,
    load_urls,
    split_documents,
)
from rag.vectorstore import add_documents_to_store, get_collection_stats

__all__ = [
    "STUDY_MATERIALS_DIR",
    "ask",
    "build_rag_chain",
    "get_collection_stats",
    "index_files",
    "index_folder",
    "index_urls",
]


def index_urls(urls_text: str) -> str:
    """Index content fetched from one or more URLs (one per line)."""
    urls = [line.strip() for line in urls_text.splitlines() if line.strip() and not line.startswith("#")]
    if not urls:
        return "No URLs provided."

    docs = load_urls(urls)
    if not docs:
        return "No content fetched from the given URLs."
    chunks = split_documents(docs)
    count = add_documents_to_store(chunks)
    stats = get_collection_stats()
    return (
        f"Fetched {len(urls)} URL(s) → {len(docs)} page(s) → {count} chunks. "
        f"Total in store: {stats['chunk_count']}."
    )


def index_files(file_paths: list[str]) -> str:
    """Index uploaded files into the vector store."""
    docs = load_documents_from_paths(file_paths)
    if not docs:
        return "No documents loaded. Supported: PDF, TXT, MD, HTML."
    chunks = split_documents(docs)
    count = add_documents_to_store(chunks)
    stats = get_collection_stats()
    return f"Indexed {len(file_paths)} file(s) → {count} chunks. Total in store: {stats['chunk_count']}."


def index_folder(folder: str | None = None) -> str:
    """Index all documents from the study materials folder."""
    docs = load_documents_from_folder(folder)
    if not docs:
        return (
            f"No documents found in {folder or STUDY_MATERIALS_DIR}. "
            "Add PDF/TXT/MD/HTML files or URLs in urls.txt."
        )
    chunks = split_documents(docs)
    count = add_documents_to_store(chunks)
    stats = get_collection_stats()
    return f"Indexed {len(docs)} document(s) → {count} chunks. Total in store: {stats['chunk_count']}."
