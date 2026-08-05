"""Privacy / network-boundary helpers.

Strict mode keeps schemas and API responses on-host: no remote fetches,
no cloud LLM, and no payload logging.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from backend.core.config import Settings


class PrivacyError(PermissionError):
    """Raised when an operation would send data outside the local boundary."""


def assert_remote_schema_allowed(settings: Settings) -> None:
    if not settings.remote_schema_fetch_enabled:
        raise PrivacyError(
            "Remote schema URL fetch is disabled (privacy/strict mode). "
            "Use Paste Text or Upload File instead so data stays local."
        )


def assert_cloud_llm_allowed(settings: Settings, provider_name: str) -> None:
    name = (provider_name or "").lower()
    if name == "groq" and not settings.cloud_llm_enabled:
        raise PrivacyError(
            "Cloud LLM (Groq) is disabled to prevent data leaving this machine. "
            "Use a local Ollama model, or set ALLOW_CLOUD_LLM=true only if you accept the risk."
        )


def assert_ollama_is_local(base_url: str) -> None:
    """Refuse non-local Ollama endpoints so prompts are not sent to remote hosts."""
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return
    # Allow Docker-internal service name only when explicitly loopback-mapped is not available;
    # still require private/local address resolution.
    if host in {"host.docker.internal", "ollama"}:
        return
    try:
        infos = socket.getaddrinfo(host, parsed.port or 11434, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise PrivacyError(f"Cannot resolve Ollama host '{host}': {exc}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not (ip.is_loopback or ip.is_private or ip.is_link_local):
            raise PrivacyError(
                f"Ollama URL host '{host}' resolves to public IP {ip}. "
                "Refusing to send schema/response data off-machine."
            )


def assert_url_safe_for_fetch(url: str) -> None:
    """
    SSRF guard for optional remote schema fetch (when explicitly enabled).
    Blocks private/link-local/metadata endpoints.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise PrivacyError("Only http/https schema URLs are allowed")
    if not parsed.hostname:
        raise PrivacyError("Schema URL is missing a hostname")

    host = parsed.hostname.lower()
    if host in {"localhost", "metadata.google.internal"}:
        raise PrivacyError("Fetching schemas from localhost/metadata hosts is blocked")

    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise PrivacyError(f"Cannot resolve schema URL host: {exc}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or str(ip) == "169.254.169.254"
        ):
            raise PrivacyError(
                f"Schema URL resolves to blocked address {ip} (SSRF protection)"
            )
