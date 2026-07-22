"""Document loading and chunking utilities."""

import re
from pathlib import Path

from langchain_community.document_loaders import (
    BSHTMLLoader,
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
    WebBaseLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.config import CHUNK_OVERLAP, CHUNK_SIZE, STUDY_MATERIALS_DIR

URL_PATTERN = re.compile(r"https?://[^\s<>\"'\])]+")


def _loader_for(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(path))
    if suffix in {".html", ".htm"}:
        return BSHTMLLoader(str(path))
    return TextLoader(str(path), encoding="utf-8")


def _extract_urls_from_text(text: str) -> list[str]:
    return list(dict.fromkeys(URL_PATTERN.findall(text)))


def load_urls(urls: list[str]) -> list[Document]:
    """Fetch and load content from web URLs."""
    documents: list[Document] = []
    seen: set[str] = set()

    for raw_url in urls:
        url = raw_url.strip().rstrip("/")
        if not url or url in seen:
            continue
        seen.add(url)

        try:
            loader = WebBaseLoader(url)
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = url
                doc.metadata["type"] = "url"
            documents.extend(docs)
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc

    return documents


def _collect_urls_from_folder(target: Path) -> list[str]:
    """Collect URLs from urls.txt and from links inside markdown files."""
    urls: list[str] = []

    urls_file = target / "urls.txt"
    if urls_file.exists():
        for line in urls_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)

    for md_file in target.glob("**/*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue
        urls.extend(_extract_urls_from_text(content))

    return list(dict.fromkeys(urls))


def load_documents_from_paths(file_paths: list[str]) -> list[Document]:
    """Load documents from explicit file paths."""
    documents: list[Document] = []
    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            continue
        loader = _loader_for(path)
        documents.extend(loader.load())

        if path.suffix.lower() in {".md", ".markdown"}:
            urls = _extract_urls_from_text(path.read_text(encoding="utf-8"))
            if urls:
                documents.extend(load_urls(urls))

    return documents


def load_documents_from_folder(folder: str | None = None) -> list[Document]:
    """Load all supported documents from the study materials folder."""
    target = Path(folder) if folder else STUDY_MATERIALS_DIR
    if not target.exists():
        return []

    documents: list[Document] = []
    patterns = {
        "**/*.pdf": PyPDFLoader,
        "**/*.txt": TextLoader,
        "**/*.md": TextLoader,
        "**/*.markdown": TextLoader,
        "**/*.html": BSHTMLLoader,
        "**/*.htm": BSHTMLLoader,
    }

    for pattern, loader_cls in patterns.items():
        kwargs = {"encoding": "utf-8"} if loader_cls is TextLoader else {}
        loader = DirectoryLoader(
            str(target),
            glob=pattern,
            loader_cls=loader_cls,
            loader_kwargs=kwargs,
            show_progress=True,
            use_multithreading=True,
        )
        try:
            documents.extend(loader.load())
        except Exception:
            continue

    url_list = _collect_urls_from_folder(target)
    if url_list:
        documents.extend(load_urls(url_list))

    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    """Split documents into retrieval-friendly chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)
