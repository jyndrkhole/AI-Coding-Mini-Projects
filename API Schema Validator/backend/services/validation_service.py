"""Orchestrates schema resolution + JSON Schema validation."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.core.logging import get_logger
from backend.models.schemas import (
    ErrorCategory,
    SchemaFormat,
    ValidationErrorDetail,
    ValidationRequest,
    ValidationResponse,
    ValidationSummary,
)
from backend.utils.schema_parser import detect_and_parse, parse_json_response
from backend.validators.json_schema_validator import SchemaValidationEngine
from backend.validators.openapi_extractor import OpenAPIExtractor

logger = get_logger(__name__)


class ValidationService:
    def __init__(self) -> None:
        self._engine = SchemaValidationEngine()
        self._extractor = OpenAPIExtractor()

    async def validate(self, request: ValidationRequest) -> ValidationResponse:
        try:
            fmt, document, _ = detect_and_parse(request.schema_content)
            instance = parse_json_response(request.response_content)

            schema, root = self._resolve_target_schema(fmt, document, request)
            is_valid, errors, summary = self._engine.validate(
                schema,
                instance,
                response_text=request.response_content,
                root_document=root,
            )

            return ValidationResponse(
                valid=is_valid,
                summary=summary,
                errors=errors,
                schema_format=fmt,
                resolved_schema=schema,
                message=(
                    "PASS: Response conforms to schema"
                    if is_valid
                    else "FAIL: Response has schema violations"
                ),
            )
        except ValueError as exc:
            logger.warning("Validation input error: %s", exc)
            return ValidationResponse(
                valid=False,
                summary=ValidationSummary(total_errors=1, other=1),
                errors=[
                    ValidationErrorDetail(
                        category=ErrorCategory.OTHER,
                        message=str(exc),
                        json_path="$",
                        schema_path="/",
                    )
                ],
                message=f"FAIL: {exc}",
            )
        except Exception as exc:
            logger.exception("Unexpected validation failure")
            return ValidationResponse(
                valid=False,
                summary=ValidationSummary(total_errors=1, other=1),
                errors=[
                    ValidationErrorDetail(
                        category=ErrorCategory.OTHER,
                        message=f"Internal validation error: {exc}",
                        json_path="$",
                        schema_path="/",
                    )
                ],
                message="FAIL: Internal error during validation",
            )

    def _resolve_target_schema(
        self,
        fmt: SchemaFormat,
        document: Dict[str, Any],
        request: ValidationRequest,
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        if fmt == SchemaFormat.JSON_SCHEMA:
            return document, document

        if fmt == SchemaFormat.OPENAPI:
            if request.path and request.method:
                return self._extractor.extract_response_schema(
                    document,
                    path=request.path,
                    method=request.method,
                    status_code=request.status_code or "200",
                )
            if request.schema_name:
                return self._extractor.extract_named_schema(document, request.schema_name)

            components = (document.get("components") or {}).get("schemas") or {}
            if len(components) == 1:
                name = next(iter(components))
                return self._extractor.extract_named_schema(document, name)

            raise ValueError(
                "OpenAPI document requires path+method (or schema_name) to select a response schema"
            )

        raise ValueError("Unrecognized schema format; provide OpenAPI or JSON Schema")
