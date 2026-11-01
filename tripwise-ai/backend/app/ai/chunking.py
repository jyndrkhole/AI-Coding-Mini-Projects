"""Split uploaded notes into overlapping chunks. Size and overlap come from settings."""


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if size < 1:
        raise ValueError("chunk size must be at least 1")
    overlap = max(0, min(overlap, size - 1))
    if len(cleaned) <= size:
        return [cleaned]
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        chunks.append(cleaned[start : start + size])
        if start + size >= len(cleaned):
            break
        start += size - overlap
    return chunks
