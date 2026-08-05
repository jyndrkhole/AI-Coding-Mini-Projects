"""Core JSON Schema validation engine using jsonschema Draft 2020-12."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from backend.core.logging import get_logger
from backend.models.schemas import (
    ErrorCategory,
    ValidationErrorDetail,
    ValidationSummary,
)
from backend.utils.format_checkers import build_format_checker
from backend.utils.json_path import (
    classify_validator,
    json_path_from_absolute,
    schema_path_from_relative,
)
from backend.utils.schema_parser import estimate_line_number
from backend.utils.schema_sanitize import sanitize_schema_types

logger = get_logger(__name__)


class SchemaValidationEngine:
    """
    Validates a JSON instance against a JSON Schema.

    OpenAPI response schemas are expected to be pre-resolved into a
    plain JSON Schema (+ optional $defs) by the OpenAPI extractor.
    """

    def __init__(self) -> None:
        self._format_checker = build_format_checker()

    def validate(
        self,
        schema: Dict[str, Any],
        instance: Any,
        *,
        response_text: str = "",
        root_document: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[ValidationErrorDetail], ValidationSummary]:
        """
        Run validation and return (is_valid, errors, summary).
        Never raises for validation failures — only for broken schemas.
        """
        schema = sanitize_schema_types(schema)
        root_document = sanitize_schema_types(root_document) if root_document else None
        try:
            validator = self._build_validator(schema, root_document)
        except SchemaError as exc:
            logger.error("Invalid schema: %s", exc)
            detail = ValidationErrorDetail(
                category=ErrorCategory.OTHER,
                message=f"Schema is invalid: {exc.message}",
                json_path="$",
                schema_path=schema_path_from_relative(getattr(exc, "path", []) or []),
                validator="schema",
            )
            summary = self._summarize([detail])
            return False, [detail], summary

        errors: List[ValidationErrorDetail] = []
        for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path)):
            errors.append(self._to_detail(err, response_text))

        # Deduplicate near-identical errors
        errors = self._dedupe(errors)
        summary = self._summarize(errors)
        return len(errors) == 0, errors, summary

    def _build_validator(
        self,
        schema: Dict[str, Any],
        root_document: Optional[Dict[str, Any]],
    ) -> Draft202012Validator:
        registry = Registry()

        # Register component schemas for $ref resolution when available
        if root_document:
            components = (
                root_document.get("components", {}).get("schemas", {})
                or root_document.get("definitions", {})
                or {}
            )
            for name, component in components.items():
                if isinstance(component, dict):
                    resource = Resource.from_contents(component, default_specification=DRAFT202012)
                    # Common OpenAPI ref styles
                    registry = registry.with_resource(f"#/components/schemas/{name}", resource)
                    registry = registry.with_resource(f"#/definitions/{name}", resource)

            # Also register $defs / definitions on the extracted schema
            for key in ("$defs", "definitions"):
                defs = schema.get(key, {})
                if isinstance(defs, dict):
                    for name, component in defs.items():
                        if isinstance(component, dict):
                            resource = Resource.from_contents(
                                component, default_specification=DRAFT202012
                            )
                            registry = registry.with_resource(f"#/{key}/{name}", resource)

        # Attach full document as root for relative refs
        if root_document:
            root_resource = Resource.from_contents(
                root_document, default_specification=DRAFT202012
            )
            registry = registry.with_resource("", root_resource)

        return Draft202012Validator(
            schema,
            registry=registry,
            format_checker=self._format_checker,
        )

    def _to_detail(self, err: Any, response_text: str) -> ValidationErrorDetail:
        json_path = json_path_from_absolute(list(err.absolute_path))
        schema_path = schema_path_from_relative(list(err.absolute_schema_path))
        category = classify_validator(err.validator, err.message)

        expected: Any = None
        actual: Any = err.instance
        if err.validator == "required" and err.validator_value:
            missing = [m for m in err.validator_value if m not in (err.instance or {})]
            expected = missing
            actual = list((err.instance or {}).keys()) if isinstance(err.instance, dict) else err.instance
        elif err.validator == "type":
            expected = err.validator_value
        elif err.validator == "enum":
            expected = err.validator_value
        elif err.validator == "additionalProperties":
            expected = "no additional properties"

        line = estimate_line_number(response_text, json_path) if response_text else None

        return ValidationErrorDetail(
            category=category,
            message=err.message,
            json_path=json_path,
            schema_path=schema_path,
            expected=expected,
            actual=self._safe_repr(actual),
            line_number=line,
            validator=str(err.validator) if err.validator else None,
        )

    @staticmethod
    def _safe_repr(value: Any, limit: int = 200) -> Any:
        if value is None or isinstance(value, (bool, int, float, str)):
            if isinstance(value, str) and len(value) > limit:
                return value[:limit] + "…"
            return value
        text = str(value)
        return text if len(text) <= limit else text[:limit] + "…"

    @staticmethod
    def _dedupe(errors: List[ValidationErrorDetail]) -> List[ValidationErrorDetail]:
        seen = set()
        unique: List[ValidationErrorDetail] = []
        for e in errors:
            key = (e.category, e.json_path, e.message)
            if key in seen:
                continue
            seen.add(key)
            unique.append(e)
        return unique

    @staticmethod
    def _summarize(errors: List[ValidationErrorDetail]) -> ValidationSummary:
        summary = ValidationSummary(total_errors=len(errors))
        for e in errors:
            if e.category == ErrorCategory.MISSING_FIELD:
                summary.missing_fields += 1
            elif e.category == ErrorCategory.INVALID_TYPE:
                summary.invalid_types += 1
            elif e.category == ErrorCategory.ENUM_VIOLATION:
                summary.enum_violations += 1
            elif e.category == ErrorCategory.ADDITIONAL_PROPERTY:
                summary.additional_properties += 1
            elif e.category == ErrorCategory.INVALID_FORMAT:
                summary.invalid_formats += 1
            else:
                summary.other += 1
        return summary
