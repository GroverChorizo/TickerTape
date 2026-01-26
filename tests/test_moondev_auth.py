import os

import pytest

from tui.feeds.moondev_client import MoonDevAuthError, MoonDevClient


class DummyResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class DummyClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers=None, params=None, **kwargs):
        self.calls.append({"method": method, "url": url, "headers": headers or {}, "params": params or {}})
        return self.responses.pop(0)

    def close(self):
        return None


def test_moondev_auth_attaches_header(monkeypatch):
    monkeypatch.setenv("MOONDEV_API_KEY", "secret-key")
    dummy = DummyClient([DummyResponse(status_code=200, payload={"ok": True})])
    client = MoonDevClient(client=dummy)

    payload = client.get_json("whales")
    assert payload["ok"] is True
    assert dummy.calls[0]["headers"]["X-API-Key"] == "secret-key"
    assert "api_key" not in dummy.calls[0]["params"]


def test_moondev_missing_key_blocks_request(monkeypatch):
    monkeypatch.delenv("MOONDEV_API_KEY", raising=False)
    dummy = DummyClient([DummyResponse(status_code=200, payload={"ok": True})])
    client = MoonDevClient(client=dummy)

    with pytest.raises(MoonDevAuthError):
        client.get_json("whales")
    assert dummy.calls == []


def test_moondev_error_redacts_secret(monkeypatch):
    monkeypatch.setenv("MOONDEV_API_KEY", "super-secret")
    dummy = DummyClient(
        [
            DummyResponse(status_code=401, text="Unauthorized"),
            DummyResponse(status_code=401, text="Unauthorized"),
        ]
    )
    client = MoonDevClient(client=dummy)

    with pytest.raises(RuntimeError) as exc:
        client.get_json("whales")
    message = str(exc.value)
    assert "super-secret" not in message
    assert "api_key=REDACTED" in message
