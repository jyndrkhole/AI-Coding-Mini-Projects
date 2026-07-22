"""Document ingestion pipeline for the knowledge base."""

import json
import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.models import Document
from app.rag.chunker import SUPPORTED_EXTENSIONS, chunk_text, load_document_text
from app.rag.vector_store import VectorStore


class IngestService:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.settings = get_settings()
        self.vector_store = vector_store or VectorStore()

    async def ingest_file(
        self,
        db: AsyncSession,
        workspace_id: int,
        source_path: Path,
        original_name: str,
        category: str = "general",
        metadata: Optional[dict] = None,
    ) -> Document:
        suffix = source_path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}")

        dest_dir = self.settings.upload_dir / f"workspace_{workspace_id}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_name = f"{uuid4().hex}{suffix}"
        dest_path = dest_dir / dest_name
        shutil.copy2(source_path, dest_path)

        doc = Document(
            workspace_id=workspace_id,
            filename=dest_name,
            original_name=original_name,
            file_type=suffix.lstrip("."),
            category=category,
            file_path=str(dest_path),
            file_size=dest_path.stat().st_size,
            status="processing",
            metadata_json=metadata or {},
        )
        db.add(doc)
        await db.flush()

        try:
            text = load_document_text(dest_path)
            chunks = chunk_text(text)
            metadatas = [
                {
                    "document_id": doc.id,
                    "workspace_id": workspace_id,
                    "filename": original_name,
                    "category": category,
                    "chunk_index": i,
                    "file_type": suffix.lstrip("."),
                }
                for i in range(len(chunks))
            ]
            await self.vector_store.add_chunks(workspace_id, chunks, metadatas)
            doc.chunk_count = len(chunks)
            doc.status = "ready"
        except Exception as exc:
            doc.status = "failed"
            doc.metadata_json = {**(doc.metadata_json or {}), "error": str(exc)}
            raise

        await db.flush()
        return doc

    async def ingest_text(
        self,
        db: AsyncSession,
        workspace_id: int,
        text: str,
        title: str,
        category: str = "notes",
        metadata: Optional[dict] = None,
    ) -> Document:
        dest_dir = self.settings.upload_dir / f"workspace_{workspace_id}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_name = f"{uuid4().hex}.txt"
        dest_path = dest_dir / dest_name
        dest_path.write_text(text, encoding="utf-8")

        doc = Document(
            workspace_id=workspace_id,
            filename=dest_name,
            original_name=title,
            file_type="txt",
            category=category,
            file_path=str(dest_path),
            file_size=dest_path.stat().st_size,
            status="processing",
            metadata_json=metadata or {},
        )
        db.add(doc)
        await db.flush()

        chunks = chunk_text(text)
        metadatas = [
            {
                "document_id": doc.id,
                "workspace_id": workspace_id,
                "filename": title,
                "category": category,
                "chunk_index": i,
                "file_type": "txt",
            }
            for i in range(len(chunks))
        ]
        await self.vector_store.add_chunks(workspace_id, chunks, metadatas)
        doc.chunk_count = len(chunks)
        doc.status = "ready"
        await db.flush()
        return doc

    async def ingest_chatgpt_export(
        self,
        db: AsyncSession,
        workspace_id: int,
        content: str,
        title: str = "ChatGPT Conversation",
    ) -> Document:
        """Import ChatGPT JSON export or plain text/markdown conversation."""
        parsed = content.strip()
        try:
            data = json.loads(parsed)
            parsed = self._extract_chatgpt_text(data)
        except json.JSONDecodeError:
            pass

        return await self.ingest_text(
            db,
            workspace_id,
            parsed,
            title=title,
            category="chatgpt_history",
            metadata={"source": "chatgpt_import"},
        )

    def _extract_chatgpt_text(self, data: object) -> str:
        """Best-effort extraction from common ChatGPT export formats."""
        lines: list[str] = []

        if isinstance(data, list):
            for item in data:
                lines.append(self._extract_chatgpt_text(item))
            return "\n\n".join(filter(None, lines))

        if isinstance(data, dict):
            # conversations.json style
            mapping = data.get("mapping")
            if isinstance(mapping, dict):
                for node in mapping.values():
                    message = (node or {}).get("message") or {}
                    author = ((message.get("author") or {}).get("role")) or "unknown"
                    content = message.get("content") or {}
                    parts = content.get("parts") or []
                    text_parts = [p for p in parts if isinstance(p, str) and p.strip()]
                    if text_parts:
                        lines.append(f"[{author.upper()}]\n" + "\n".join(text_parts))
                return "\n\n".join(lines)

            # Simple messages array
            messages = data.get("messages") or data.get("conversation")
            if isinstance(messages, list):
                for msg in messages:
                    if not isinstance(msg, dict):
                        continue
                    role = msg.get("role") or msg.get("author") or "unknown"
                    content = msg.get("content") or msg.get("text") or ""
                    if isinstance(content, list):
                        content = "\n".join(str(c) for c in content)
                    if content:
                        lines.append(f"[{str(role).upper()}]\n{content}")
                return "\n\n".join(lines)

            title = data.get("title")
            if title:
                lines.append(f"# {title}")
            for key in ("text", "content", "body"):
                if key in data and isinstance(data[key], str):
                    lines.append(data[key])
            return "\n\n".join(lines)

        return str(data)
