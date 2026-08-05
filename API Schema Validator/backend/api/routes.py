"""REST API routes for schema load, validate, explain, export, health."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.llm.providers import LLMService
from backend.models.schemas import (
    ExplainRequest,
    ExplainResponse,
    ExportRequest,
    HealthResponse,
    PrivacyPolicy,
    SchemaFormat,
    SchemaLoadRequest,
    SchemaLoadResponse,
    SchemaSourceType,
    ValidationRequest,
    ValidationResponse,
)
from backend.services.export_service import ExportService
from backend.services.schema_loader import SchemaLoaderService
from backend.services.validation_service import ValidationService

logger = get_logger(__name__)

router = APIRouter(prefix="/api")

_loader = SchemaLoaderService()
_validator = ValidationService()
_exporter = ExportService()
_llm = LLMService()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        llm_provider=settings.llm_provider,
        privacy=PrivacyPolicy(
            mode=settings.privacy_mode,
            remote_schema_fetch=settings.remote_schema_fetch_enabled,
            cloud_llm=settings.cloud_llm_enabled,
            local_llm=settings.allow_local_llm,
            payload_logging=settings.payload_logging_enabled,
        ),
    )


@router.post("/schema/load", response_model=SchemaLoadResponse)
async def load_schema(
    source_type: SchemaSourceType = Form(...),
    content: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
) -> SchemaLoadResponse:
    """
    Load a schema from URL, uploaded file, or pasted text.
    Accepts multipart form so large files upload cleanly.
    """
    file_bytes: Optional[bytes] = None
    if file is not None:
        file_bytes = await file.read()

    request = SchemaLoadRequest(source_type=source_type, content=content, url=url)
    result = await _loader.load(request, file_content=file_bytes)
    if not result.success:
        # Avoid logging schema/URL contents — error message only.
        logger.warning("Schema load returned error (no payload logged)")
    return result


@router.post("/schema/load/json", response_model=SchemaLoadResponse)
async def load_schema_json(request: SchemaLoadRequest) -> SchemaLoadResponse:
    """JSON body variant for text/url loads without multipart."""
    if request.source_type == SchemaSourceType.URL and not get_settings().remote_schema_fetch_enabled:
        return SchemaLoadResponse(
            success=False,
            format=SchemaFormat.UNKNOWN,
            error=(
                "Remote schema URL fetch is disabled (privacy/strict mode). "
                "Use Paste Text or Upload File instead."
            ),
            message="Blocked by privacy policy",
        )
    return await _loader.load(request)


@router.post("/schema/validate", response_model=ValidationResponse)
async def validate_schema(request: ValidationRequest) -> ValidationResponse:
    settings = get_settings()
    if len(request.response_content.encode("utf-8")) > settings.max_payload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Response exceeds {settings.max_payload_size_mb} MB limit",
        )
    if len(request.schema_content.encode("utf-8")) > settings.max_payload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Schema exceeds {settings.max_payload_size_mb} MB limit",
        )
    return await _validator.validate(request)


@router.post("/schema/explain", response_model=ExplainResponse)
async def explain_schema(request: ExplainRequest) -> ExplainResponse:
    """Optional AI assistance — never invoked by core validation."""
    return await _llm.explain(request)


@router.post("/schema/export")
async def export_report(request: ExportRequest) -> Response:
    content, media_type, filename = _exporter.export(request)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
