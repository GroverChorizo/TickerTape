"""Deterministic, local-only cache with safe keying and metadata sidecar.

- Keys are sanitized via an allowlist; otherwise sha256(key) is used
- Paths are resolved with pathlib to prevent traversal
- Metadata sidecar stores content hash, schema_version, and timestamps
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from pathlib import Path
import hashlib
import json
import re

DEFAULT_CACHE_ROOT = Path("./local_cache")
_ALLOWED_KEY_RE = re.compile(r"^[a-z0-9._-]{1,128}$")


def _safe_key(key: str) -> str:
    """Return a safe filename for the given key.

    If key matches allowlist regex it is returned unchanged; otherwise a sha256 hex is used.
    """
    if _ALLOWED_KEY_RE.match(key):
        return key
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"k_{h}"


def _content_hash(content_bytes: bytes) -> str:
    return hashlib.sha256(content_bytes).hexdigest()


class LocalCache:
    def __init__(self, root: Optional[Path] = None, schema_version: str = "1") -> None:
        self.root = (root or DEFAULT_CACHE_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.schema_version = schema_version

    def _path_for(self, key: str) -> Path:
        safe = _safe_key(key)
        path = (self.root / f"{safe}.json").resolve()
        # Ensure the resolved path is inside root
        if self.root not in path.parents and path != self.root:
            raise ValueError("Resolved cache path escapes cache root")
        return path

    def _meta_path_for(self, key: str) -> Path:
        safe = _safe_key(key)
        return (self.root / f"{safe}.meta.json").resolve()

    def save(self, key: str, obj: Any) -> None:
        path = self._path_for(key)
        # Deterministic JSON serialization
        payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        content_hash = _content_hash(payload)
        path.write_bytes(payload)

        from datetime import datetime, timezone

        meta = {
            "schema_version": self.schema_version,
            "content_hash": content_hash,
            "size": len(payload),
            # timezone-aware UTC timestamp
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        meta_path = self._meta_path_for(key)
        meta_path.write_text(json.dumps(meta, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    def load(self, key: str) -> Any:
        path = self._path_for(key)
        if not path.exists():
            raise FileNotFoundError(f"Cache key '{key}' not found")
        raw = path.read_bytes()
        # Validate metadata if present
        meta_path = self._meta_path_for(key)
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta.get("content_hash") != _content_hash(raw):
                    raise ValueError("Cache content hash mismatch")
            except Exception as e:
                raise ValueError(f"Cache metadata invalid: {e}")
        return json.loads(raw.decode("utf-8"))

    def exists(self, key: str) -> bool:
        return self._path_for(key).exists()

    def meta(self, key: str) -> Optional[Dict[str, Any]]:
        meta_path = self._meta_path_for(key)
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text(encoding="utf-8"))