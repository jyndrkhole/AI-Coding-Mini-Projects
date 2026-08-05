"""Schema loading service — URL / file / text → parsed metadata."""

from __future__ import annotations

from typing import Optional

import httpx

from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.core.privacy import (
    PrivacyError,
    assert_remote_schema_allowed,
    assert_url_safe_for_fetch,
)
from backend.models.schemas import (
    SchemaFormat,
    SchemaLoadRequest,
    SchemaLoadResponse,
    SchemaOption,
    SchemaSourceType,
)
from backend.utils.schema_parser import detect_and_parse
from backend.validators.openapi_extractor import OpenAPIExtractor

logger = get_logger(__name__)


class SchemaLoaderService:
    def __init__(self) -> None:
        self._extractor = OpenAPIExtractor()

    async def load(
        self, request: SchemaLoadRequest, file_content: Optional[bytes] = None
    ) -> SchemaLoadResponse:
        settings = get_settings()
        try:
            raw = await self._resolve_content(request, file_content, settings)
            fmt, data, normalized = detect_and_parse(raw)
            title = None
            if isinstance(data.get("info"), dict):
                title = data["info"].get("title")
            else:
                title = data.get("title")

            endpoints = []
            schemas: list[SchemaOption] = []
            openapi_version = None

            if fmt == SchemaFormat.OPENAPI:
                openapi_version = data.get("openapi") or data.get("swagger")
                endpoints = self._extractor.list_endpoints(data)
                schemas = self._extractor.list_component_schemas(data)
            elif fmt == SchemaFormat.JSON_SCHEMA:
                name = data.get("title") or "RootSchema"
                schemas = [
                    SchemaOption(
                        name=str(name),
                        path="#",
                        description=data.get("description"),
                    )
                ]

            media = (
                "application/json"
                if raw.lstrip().startswith("{")
                else "application/x-yaml"
            )

            return SchemaLoadResponse(
                success=True,
                format=fmt,
                openapi_version=str(openapi_version) if openapi_version else None,
                title=title,
                endpoints=endpoints,
                schemas=schemas,
                schema_text=normalized,
                detected_media_type=media,
                message=f"Loaded {fmt.value} document successfully",
            )
        except PrivacyError as exc:
            logger.warning("Schema load blocked by privacy policy")
            return SchemaLoadResponse(
                success=False,
                format=SchemaFormat.UNKNOWN,
                error=str(exc),
                message="Blocked by privacy policy",
            )
        except Exception as exc:
            # Never log schema/body contents — only the exception class/message.
            logger.exception("Schema load failed: %s", type(exc).__name__)
            return SchemaLoadResponse(
                success=False,
                format=SchemaFormat.UNKNOWN,
                error=str(exc),
                message="Failed to load schema",
            )

    async def _resolve_content(
        self,
        request: SchemaLoadRequest,
        file_content: Optional[bytes],
        settings,
    ) -> str:
        if request.source_type == SchemaSourceType.TEXT:
            if not request.content:
                raise ValueError("content is required when source_type is text")
            return request.content

        if request.source_type == SchemaSourceType.FILE:
            if file_content is None:
                raise ValueError("file upload is required when source_type is file")
            if len(file_content) > settings.max_payload_bytes:
                raise ValueError(
                    f"File exceeds max size of {settings.max_payload_size_mb} MB"
                )
            return file_content.decode("utf-8")

        if request.source_type == SchemaSourceType.URL:
            if not request.url:
                raise ValueError("url is required when source_type is url")
            assert_remote_schema_allowed(settings)
            assert_url_safe_for_fetch(request.url)
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=False,  # avoid redirect-based SSRF hops
            ) as client:
                resp = await client.get(request.url)
                resp.raise_for_status()
                if len(resp.content) > settings.max_payload_bytes:
                    raise ValueError(
                        f"Remote schema exceeds max size of {settings.max_payload_size_mb} MB"
                    )
                return resp.text

        raise ValueError(f"Unsupported source_type: {request.source_type}")
