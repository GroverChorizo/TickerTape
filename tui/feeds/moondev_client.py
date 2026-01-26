"""MoonDev API client with auth injection and safe error reporting."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import logging
import random
import time

from backend.secrets import moondev_config_help, resolve_moondev_api_key
from .url_builder import EndpointUrlBuilder

logger = logging.getLogger(__name__)


class MoonDevAuthError(RuntimeError):
    """Raised when MoonDev auth is missing or invalid."""


@dataclass(frozen=True)
class MoonDevAuth:
    api_key: str
    source: str


class MoonDevClient:
    def __init__(
        self,
        base_url: str = "https://api.moondev.com",
        timeout: float = 10.0,
        retries: int = 3,
        client: Optional[Any] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        if client is None:
            import httpx

            self._httpx = httpx
            self._client = httpx.Client(timeout=httpx.Timeout(timeout))
        else:
            self._httpx = None
            self._client = client
        self._url_builder = EndpointUrlBuilder(self.base_url)

    def close(self) -> None:
        self._client.close()

    def get_json(self, endpoint_key: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        url = self._url_builder.build(endpoint_key, **kwargs)
        return self._request("GET", url, params=params)

    def post_json(self, endpoint_key: str, payload: Dict[str, Any], **kwargs: Any) -> Any:
        url = self._url_builder.build(endpoint_key, **kwargs)
        return self._request("POST", url, json=payload)

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        auth = self._resolve_auth()
        headers = dict(kwargs.pop("headers", {}))
        headers["X-API-Key"] = auth.api_key
        last_exc: Optional[Exception] = None
        last_error: Optional[str] = None
        for attempt in range(1, self.retries + 1):
            try:
                response, used_query, used_params = self._send_with_auth(
                    method,
                    url,
                    headers=headers,
                    use_query_param=False,
                    **kwargs,
                )
                if response.status_code == 401:
                    response, used_query, used_params = self._send_with_auth(
                        method,
                        url,
                        headers=headers,
                        use_query_param=True,
                        **kwargs,
                    )
                sanitized_url = _sanitize_url(url, used_params, used_query)
                logger.info(
                    {
                        "event": "http_request",
                        "method": method,
                        "url": sanitized_url,
                        "status": response.status_code,
                        "attempt": attempt,
                    }
                )
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    last_error = _format_http_error(method, sanitized_url, response)
                    last_exc = RuntimeError(last_error)
                    time.sleep(self._backoff(attempt))
                    continue
                if 400 <= response.status_code < 500:
                    raise RuntimeError(_format_http_error(method, sanitized_url, response))
                try:
                    return response.json()
                except Exception:
                    raise RuntimeError(_format_json_error(method, sanitized_url, response))
            except Exception as exc:
                if self._httpx and isinstance(exc, self._httpx.RequestError):
                    last_exc = exc
                    last_error = f"{method} {_sanitize_url(url, kwargs.get('params'), False)} -> Request error: {exc}"
                    logger.warning(
                        {
                            "event": "http_error",
                            "url": _sanitize_url(url, kwargs.get('params'), False),
                            "attempt": attempt,
                            "error": str(exc),
                        }
                    )
                    time.sleep(self._backoff(attempt))
                    continue
                raise
        if last_error:
            raise ConnectionError(last_error)
        raise ConnectionError(f"Failed to fetch {url}: {last_exc}")

    def _resolve_auth(self) -> MoonDevAuth:
        key, source = resolve_moondev_api_key()
        if not key:
            raise MoonDevAuthError(moondev_config_help())
        return MoonDevAuth(api_key=key, source=source or "unknown")

    def _send_with_auth(
        self,
        method: str,
        url: str,
        *,
        headers: Dict[str, str],
        use_query_param: bool,
        **kwargs: Any,
    ) -> Tuple[Any, bool, Dict[str, Any]]:
        params = dict(kwargs.pop("params", {}) or {})
        if use_query_param:
            params["api_key"] = headers.get("X-API-Key", "")
        response = self._client.request(method, url, headers=headers, params=params, **kwargs)
        return response, use_query_param, params

    @staticmethod
    def _backoff(attempt: int) -> float:
        return 0.5 * (2 ** (attempt - 1)) + random.uniform(0, 0.25)


def _sanitize_url(url: str, params: Optional[Dict[str, Any]], used_query: bool) -> str:
    if not used_query or not params:
        return url
    safe_params = []
    for key, value in params.items():
        if key == "api_key":
            safe_params.append(f"{key}=REDACTED")
        else:
            safe_params.append(f"{key}={value}")
    return f"{url}?{'&'.join(safe_params)}"


def _format_http_error(method: str, url: str, response: Any) -> str:
    snippet = ""
    try:
        snippet = str(getattr(response, "text", "") or "")
    except Exception:
        snippet = ""
    snippet = snippet.replace("\r", " ").replace("\n", " ")[:200]
    return f"{method} {url} -> HTTP {response.status_code}: {snippet}"


def _format_json_error(method: str, url: str, response: Any) -> str:
    snippet = ""
    try:
        snippet = str(getattr(response, "text", "") or "")
    except Exception:
        snippet = ""
    snippet = snippet.replace("\r", " ").replace("\n", " ")[:200]
    return f"{method} {url} -> HTTP {response.status_code} (json decode error): {snippet}"
