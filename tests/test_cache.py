import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import json
import pytest
from backend.cache import LocalCache


def test_cache_save_load_roundtrip(tmp_path):
    cache = LocalCache(root=tmp_path)
    key = "testkey"
    data = {"a": 1, "b": [2, 3]}
    cache.save(key, data)
    loaded = cache.load(key)
    assert loaded == data

    meta = cache.meta(key)
    assert meta is not None
    assert meta["schema_version"] == cache.schema_version


def test_cache_safe_key_and_no_traversal(tmp_path):
    cache = LocalCache(root=tmp_path)
    dangerous = "../secret.txt"
    # saving with a dangerous key should not escape root (safe key will be hashed)
    cache.save(dangerous, {"x": 1})
    # ensure file exists under root
    assert cache.exists(dangerous)
    meta = cache.meta(dangerous)
    assert "content_hash" in meta


def test_cache_content_hash_mismatch(tmp_path):
    cache = LocalCache(root=tmp_path)
    key = "mismatch"
    cache.save(key, {"v": 1})
    # tamper with content bytes
    path = tmp_path / "mismatch.json"
    path.write_text(json.dumps({"v": 2}))
    with pytest.raises(ValueError):
        cache.load(key)