"""OpenAPI document helpers: list endpoints and extract response schemas."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from backend.core.logging import get_logger
from backend.models.schemas import EndpointInfo, SchemaOption

logger = get_logger(__name__)

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


class OpenAPIExtractor:
    """Extract navigation metadata and response JSON Schemas from OpenAPI docs."""

    def list_endpoints(self, document: Dict[str, Any]) -> List[EndpointInfo]:
        endpoints: List[EndpointInfo] = []
        paths = document.get("paths") or {}
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                responses = operation.get("responses") or {}
                codes = sorted(str(c) for c in responses.keys())
                endpoints.append(
                    EndpointInfo(
                        path=path,
                        method=method.upper(),
                        operation_id=operation.get("operationId"),
                        summary=operation.get("summary"),
                        response_codes=codes or ["200"],
                    )
                )
        return endpoints

    def list_component_schemas(self, document: Dict[str, Any]) -> List[SchemaOption]:
        schemas = (document.get("components") or {}).get("schemas") or document.get("definitions") or {}
        options: List[SchemaOption] = []
        for name, schema in schemas.items():
            desc = None
            if isinstance(schema, dict):
                desc = schema.get("description") or schema.get("title")
            options.append(SchemaOption(name=name, path=f"#/components/schemas/{name}", description=desc))
        return options

    def extract_response_schema(
        self,
        document: Dict[str, Any],
        path: str,
        method: str,
        status_code: str = "200",
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Resolve the response body schema for a concrete operation.

        Returns (json_schema, root_document_for_refs).
        """
        paths = document.get("paths") or {}
        if path not in paths:
            raise ValueError(f"Path '{path}' not found in OpenAPI document")

        path_item = paths[path]
        op = path_item.get(method.lower()) or path_item.get(method.upper())
        if not isinstance(op, dict):
            raise ValueError(f"Method '{method}' not found for path '{path}'")

        responses = op.get("responses") or {}
        response = (
            responses.get(str(status_code))
            or responses.get(int(status_code) if str(status_code).isdigit() else status_code)
            or responses.get("default")
        )
        if response is None:
            available = ", ".join(str(k) for k in responses.keys()) or "(none)"
            raise ValueError(
                f"Status code '{status_code}' not found for {method.upper()} {path}. "
                f"Available: {available}"
            )

        # OAS3 uses content; Swagger 2 uses schema
        schema: Optional[Dict[str, Any]] = None
        if "content" in response:
            content = response["content"] or {}
            # Prefer application/json
            media = (
                content.get("application/json")
                or content.get("application/vnd.api+json")
                or next(iter(content.values()), None)
            )
            if media and isinstance(media, dict):
                schema = media.get("schema")
        elif "schema" in response:
            schema = response.get("schema")

        if schema is None:
            raise ValueError(
                f"No response body schema defined for {method.upper()} {path} [{status_code}]"
            )

        resolved = self._resolve_refs(schema, document, seen=set())
        # Bundle component schemas into $defs for local validation
        bundled = self._bundle_components(resolved, document)
        return bundled, document

    def extract_named_schema(
        self, document: Dict[str, Any], schema_name: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        schemas = (document.get("components") or {}).get("schemas") or document.get("definitions") or {}
        if schema_name not in schemas:
            raise ValueError(f"Schema '{schema_name}' not found in components/schemas")
        resolved = self._resolve_refs(schemas[schema_name], document, seen=set())
        bundled = self._bundle_components(resolved, document)
        return bundled, document

    def _resolve_refs(
        self,
        node: Any,
        document: Dict[str, Any],
        seen: set,
        depth: int = 0,
    ) -> Any:
        """Deep-copy and inline local $ref pointers (best-effort, cycle-safe)."""
        if depth > 64:
            return node

        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                ref = node["$ref"]
                if ref in seen:
                    return {"description": f"Circular reference to {ref}"}
                target = self._lookup_ref(document, ref)
                if target is None:
                    return copy.deepcopy(node)
                seen.add(ref)
                resolved = self._resolve_refs(copy.deepcopy(target), document, seen, depth + 1)
                # Merge sibling keywords (OpenAPI allows siblings beside $ref)
                siblings = {k: v for k, v in node.items() if k != "$ref"}
                if siblings and isinstance(resolved, dict):
                    merged = copy.deepcopy(resolved)
                    merged.update(
                        {
                            k: self._resolve_refs(v, document, seen, depth + 1)
                            for k, v in siblings.items()
                        }
                    )
                    seen.discard(ref)
                    return merged
                seen.discard(ref)
                return resolved

            return {
                k: self._resolve_refs(v, document, seen, depth + 1) for k, v in node.items()
            }

        if isinstance(node, list):
            return [self._resolve_refs(item, document, seen, depth + 1) for item in node]

        return node

    @staticmethod
    def _lookup_ref(document: Dict[str, Any], ref: str) -> Optional[Any]:
        if not ref.startswith("#/"):
            logger.warning("External $ref not supported: %s", ref)
            return None
        parts = ref[2:].split("/")
        cursor: Any = document
        for part in parts:
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(cursor, dict) or part not in cursor:
                logger.warning("Unresolved $ref: %s", ref)
                return None
            cursor = cursor[part]
        return cursor

    def _bundle_components(self, schema: Dict[str, Any], document: Dict[str, Any]) -> Dict[str, Any]:
        """Attach component schemas under $defs for Draft 2020-12 validators."""
        bundled = copy.deepcopy(schema) if isinstance(schema, dict) else {"type": "object"}
        components = (document.get("components") or {}).get("schemas") or {}
        if components:
            defs = bundled.setdefault("$defs", {})
            for name, component in components.items():
                if name not in defs and isinstance(component, dict):
                    # Keep unresolved copies; registry also handles refs
                    defs[name] = copy.deepcopy(component)
        return bundled
