import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import pytest
from backend.network import NetworkClient
import httpx

pytest.importorskip("textual")
pytest.importorskip("httpx")


class DummyResponse:
    def __init__(self, status_code:int, json_obj=None):
        self.status_code = status_code
        self._json = json_obj or {}
    def json(self):
        return self._json


class DummyClient:
    def __init__(self, responses):
        # responses: list of either Exception or DummyResponse
        self._responses = responses
        self.calls = 0
    def get(self, url, params=None):
        resp = self._responses[self.calls]
        self.calls += 1
        if isinstance(resp, Exception):
            raise resp
        return resp
    def close(self):
        pass


def test_retry_on_transient_error_then_success(monkeypatch):
    # Simulate network error first, then 200
    transient = httpx.RequestError("timeout")
    success = DummyResponse(200, json_obj={"ok": True})
    client = DummyClient([transient, success])
    net = NetworkClient(base_url="https://example.com", retries=2, client=client)

    data = net.get("whales")
    assert data == {"ok": True}
    assert client.calls == 2


def test_do_not_retry_on_4xx(monkeypatch):
    # Simulate 400 response
    bad = DummyResponse(400, json_obj={"err": "bad"})
    client = DummyClient([bad])
    net = NetworkClient(base_url="https://example.com", retries=2, client=client)
    with pytest.raises(httpx.HTTPStatusError):
        net.get("whales")
    assert client.calls == 1