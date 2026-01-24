"""Network client with strict policy and sanitized logging.

- BASE_URL must be configured from Vision or runtime configuration
- Endpoints are mapped to path templates (no guessed absolute URLs)
- Retries on transient errors (5xx, timeouts); do NOT retry on 4xx
- No raw payload logging; only metadata and sanitized summaries
"""
from __future__ import annotations
import time
from typing import Any, Dict, Optional
import httpx
import logging

from .logging_config import get_logger

logger = get_logger(__name__)

# Implementation-defined base URL; should be set from configuration
# Canonical base URL per Vision (see WhaleWatch/TickerTape/BtheVision_v1_5_5.txt)
BASE_URL: str = "https://api.hyperliquid.xyz"  # Source: BtheVision_v1_5_5.txt

# Endpoint paths derived from Vision where available. Do not invent new endpoints.
ENDPOINT_PATHS: Dict[str, str] = {
    "whales": "/api/whales.json",
    "liquidations_stats": "/api/liquidations/stats.json",
    "funding": "/api/funding.json",
    "candles": "/api/candleSnapshot",
    # Add or update paths from Vision only
}

DEFAULT_TIMEOUT = 10.0  # seconds
DEFAULT_RETRIES = 3
BACKOFF_FACTOR = 0.5  # seconds, exponential backoff


class NetworkClient:
    """Simple httpx wrapper with retry logic for transient errors.

    Usage:
        client = NetworkClient(base_url=...)  # base_url can be set at runtime
        data = client.get("whales", params={"symbol": "BTCUSD"})
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        client: Optional[httpx.Client] = None,
    ) -> None:
        """Create a NetworkClient.

        Args:
            base_url: Base URL to prefix endpoint paths (set from Vision in production)
            timeout: Request timeout in seconds
            retries: Number of attempts for transient errors
            client: Optional httpx.Client instance for dependency injection (tests)
        """
        self.base_url = base_url or BASE_URL
        self.timeout = timeout
        self.retries = retries
        # Allow injection of a httpx.Client for testability
        self._client = client or httpx.Client(timeout=httpx.Timeout(timeout))

    def _build_url(self, endpoint_key: str) -> str:
        if endpoint_key not in ENDPOINT_PATHS:
            raise ValueError(f"Endpoint '{endpoint_key}' is not in allowlist")
        path = ENDPOINT_PATHS[endpoint_key]
        return f"{self.base_url.rstrip('/')}{path}"

    def get(self, endpoint_key: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint_key)
        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt < self.retries:
            attempt += 1
            start = time.time()
            try:
                resp = self._client.get(url, params=params)
                elapsed_ms = int((time.time() - start) * 1000)
                # Sanitize logging: do not include response text/body
                logger.info(
                    {
                        "event": "http_request",
                        "endpoint": endpoint_key,
                        "status": resp.status_code,
                        "elapsed_ms": elapsed_ms,
                        "attempt": attempt,
                    }
                )

                # Retry on 5xx only
                if 500 <= resp.status_code < 600:
                    last_exc = RuntimeError(f"Server error: {resp.status_code}")
                    logger.warning(
                        {"event": "http_transient_error", "endpoint": endpoint_key, "status": resp.status_code, "attempt": attempt}
                    )
                    time.sleep(BACKOFF_FACTOR * (2 ** (attempt - 1)))
                    continue

                if 400 <= resp.status_code < 500:
                    # Client errors are not retried
                    logger.error({"event": "http_client_error", "endpoint": endpoint_key, "status": resp.status_code})
                    # httpx.Response.raise_for_status() raises HTTPStatusError; emulate that for test doubles
                    raise httpx.HTTPStatusError(f"Client error: {resp.status_code}", request=None, response=None)

                # Success
                try:
                    return resp.json()
                except Exception as e:
                    logger.error({"event": "json_decode_error", "endpoint": endpoint_key, "err": str(e)})
                    raise
            except httpx.RequestError as e:
                # Network-level transient error; retry
                last_exc = e
                logger.warning({"event": "network_error", "endpoint": endpoint_key, "err": str(e), "attempt": attempt})
                time.sleep(BACKOFF_FACTOR * (2 ** (attempt - 1)))
                continue
            except Exception as e:
                # Non-retriable or unknown
                logger.error({"event": "fetch_error", "endpoint": endpoint_key, "err": str(e)})
                raise
        # Exhausted retries
        logger.error(f"Failed to fetch {endpoint_key} after {self.retries} attempts: {last_exc!r}")
        raise ConnectionError(f"Failed to fetch {endpoint_key}")

    def close(self) -> None:
        self._client.close()


# Module-level helper for quick use
_default_client: Optional[NetworkClient] = None


def get_default_client() -> NetworkClient:
    global _default_client
    if _default_client is None:
        _default_client = NetworkClient()
    return _default_client