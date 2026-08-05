"""Pydantic request/response models for the Schema Validator API."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SchemaSourceType(str, Enum):
    URL = "url"
    FILE = "file"
    TEXT = "text"


class ResponseSourceType(str, Enum):
    TEXT = "text"
    FILE = "file"


class SchemaFormat(str, Enum):
    OPENAPI = "openapi"
    JSON_SCHEMA = "json_schema"
    UNKNOWN = "unknown"


class LLMAction(str, Enum):
    EXPLAIN_ERRORS = "explain_errors"
    SUGGEST_FIX = "suggest_fix"
    GENERATE_CORRECT_JSON = "generate_correct_json"
    EXPLAIN_SCHEMA = "explain_schema"


class ErrorCategory(str, Enum):
    MISSING_FIELD = "missing_field"
    INVALID_TYPE = "invalid_type"
    ENUM_VIOLATION = "enum_violation"
    ADDITIONAL_PROPERTY = "additional_property"
    INVALID_FORMAT = "invalid_format"
    ONE_OF = "one_of"
    ANY_OF = "any_of"
    ALL_OF = "all_of"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Schema load
# ---------------------------------------------------------------------------


class SchemaLoadRequest(BaseModel):
    source_type: SchemaSourceType
    content: Optional[str] = Field(
        default=None, description="Raw schema text when source_type is text"
    )
    url: Optional[str] = Field(
        default=None, description="Remote schema URL when source_type is url"
    )


class EndpointInfo(BaseModel):
    path: str
    method: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    response_codes: List[str] = Field(default_factory=list)


class SchemaOption(BaseModel):
    name: str
    path: Optional[str] = None
    description: Optional[str] = None


class SchemaLoadResponse(BaseModel):
    success: bool
    format: SchemaFormat
    openapi_version: Optional[str] = None
    title: Optional[str] = None
    endpoints: List[EndpointInfo] = Field(default_factory=list)
    schemas: List[SchemaOption] = Field(default_factory=list)
    schema_text: Optional[str] = None
    detected_media_type: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationRequest(BaseModel):
    schema_content: str = Field(..., description="OpenAPI or JSON Schema document")
    response_content: str = Field(..., description="JSON response body to validate")
    path: Optional[str] = Field(default=None, description="OpenAPI path e.g. /users/{id}")
    method: Optional[str] = Field(default=None, description="HTTP method e.g. GET")
    status_code: Optional[str] = Field(default="200", description="Response status code")
    schema_name: Optional[str] = Field(
        default=None, description="Named component schema when not using path/method"
    )


class ValidationErrorDetail(BaseModel):
    category: ErrorCategory
    message: str
    json_path: str = Field(description="JSONPath-like location in the response")
    schema_path: str = Field(description="Path within the schema document")
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    line_number: Optional[int] = None
    validator: Optional[str] = None


class ValidationSummary(BaseModel):
    total_errors: int = 0
    missing_fields: int = 0
    invalid_types: int = 0
    enum_violations: int = 0
    additional_properties: int = 0
    invalid_formats: int = 0
    other: int = 0


class ValidationResponse(BaseModel):
    valid: bool
    summary: ValidationSummary
    errors: List[ValidationErrorDetail] = Field(default_factory=list)
    schema_format: SchemaFormat = SchemaFormat.UNKNOWN
    resolved_schema: Optional[Dict[str, Any]] = None
    message: str = ""


# ---------------------------------------------------------------------------
# AI explain
# ---------------------------------------------------------------------------


class ExplainRequest(BaseModel):
    action: LLMAction
    schema_content: Optional[str] = None
    response_content: Optional[str] = None
    errors: List[ValidationErrorDetail] = Field(default_factory=list)
    provider: Optional[str] = None
    model: Optional[str] = None


class ExplainResponse(BaseModel):
    success: bool
    action: LLMAction
    content: str = ""
    provider: Optional[str] = None
    model: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class ExportFormat(str, Enum):
    HTML = "html"
    JSON = "json"
    PDF = "pdf"


class ExportRequest(BaseModel):
    format: ExportFormat
    validation_result: ValidationResponse
    schema_content: Optional[str] = None
    response_content: Optional[str] = None


class PrivacyPolicy(BaseModel):
    mode: str
    remote_schema_fetch: bool
    cloud_llm: bool
    local_llm: bool
    payload_logging: bool
    data_residency: str = (
        "Schemas and API responses stay on this host. "
        "Core validation never calls external services."
    )


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    llm_provider: str
    privacy: PrivacyPolicy
