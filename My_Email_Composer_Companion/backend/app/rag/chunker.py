"""Document loading and chunking utilities."""

from pathlib import Path
from functools import lru_cache

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


@lru_cache
def get_ocr_engine():
    """Create the OCR engine lazily so non-image imports stay lightweight."""
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def load_document_text(file_path: Path) -> str:
    """Extract plain text from supported document types."""
    suffix = file_path.suffix.lower()

    if suffix in {".txt", ".md", ".markdown", ".json"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)
        return "\n\n".join(pages)

    if suffix == ".docx":
        from docx import Document as DocxDocument

        doc = DocxDocument(str(file_path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    if suffix in IMAGE_EXTENSIONS:
        from PIL import Image
        import numpy as np

        ocr = get_ocr_engine()
        image = np.array(Image.open(file_path).convert("RGB"))
        result, _ = ocr(image)
        if not result:
            return ""
        lines = [item[1] for item in result if len(item) >= 2 and item[1].strip()]
        return "\n".join(lines)

    raise ValueError(f"Unsupported file type: {suffix}")


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if c.strip()]
