from __future__ import annotations

from providers.base import Provider
from providers.diagnostics import diagnose_provider
from commands.diagnose import diagnose_command


class DummyProvider(Provider):
    def diagnostics(self):
        return {"http": "ok", "ws": "not_configured"}

    def get_ticks(self, symbol: str):
        raise NotImplementedError

    def get_orderbook(self, symbol: str):
        raise NotImplementedError

    def get_liquidations(self):
        raise NotImplementedError

    def get_whale_trades(self):
        raise NotImplementedError

    def get_funding_rates(self):
        raise NotImplementedError

    def get_positions(self):
        raise NotImplementedError

    def close(self) -> None:
        pass


def test_diagnose_provider_latency_and_fields():
    report = diagnose_provider(DummyProvider())
    assert report["http"] == "ok"
    assert report["ws"] == "not_configured"
    assert isinstance(report["latency_ms"], float)


def test_diagnose_command_formats_output():
    output = diagnose_command(DummyProvider())
    assert "http=ok" in output
    assert "ws=not_configured" in output
    assert "latency_ms=" in output
