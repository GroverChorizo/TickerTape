from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from typing import Iterable

# Query params that must NEVER appear in UI/logs
_SENSITIVE_QUERY_KEYS = {
    "api_key",
    "apikey",
    "key",
    "token",
    "access_token",
    "authorization",
}

# Headers that must NEVER appear in UI/logs
_SENSITIVE_HEADER_KEYS = {
    "authorization",
    "x-api-key",
    "api-key",
    "apikey",
    "token",
}


def redact_url(url: str, sensitive_keys: Iterable[str] | None = None) -> str:
    """
    Return a redacted version of a URL safe for UI/logs.

    - Removes or replaces sensitive query params (api_key, token, etc.)
    - Preserves scheme, host, path, and NON-sensitive params
    - Never raises; on parse failure, returns '<redacted-url>'

    Example:
        https://api.moondev.com/x?api_key=ABC&foo=1
        -> https://api.moondev.com/x?api_key=<redacted>&foo=1
    """
    try:
        parts = urlsplit(url)
        sensitive = {k.lower() for k in (sensitive_keys or _SENSITIVE_QUERY_KEYS)}

        query_items = []
        for k, v in parse_qsl(parts.query, keep_blank_values=True):
            if k.lower() in sensitive:
                query_items.append((k, "<redacted>"))
            else:
                query_items.append((k, v))

        redacted_query = urlencode(query_items, doseq=True)

        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            redacted_query,
            parts.fragment,
        ))
    except Exception:
        # Fail closed — never echo the original string
        return "<redacted-url>"


def redact_headers(headers: dict | None) -> dict:
    """
    Return a copy of headers with sensitive values redacted.
    Safe for debug/UI use.
    """
    if not headers:
        return {}

    out: dict = {}
    for k, v in headers.items():
        if k.lower() in _SENSITIVE_HEADER_KEYS:
            out[k] = "<redacted>"
        else:
            out[k] = v
    return out
