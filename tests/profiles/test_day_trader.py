import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.ui.screens.profile_day_trader import DayTraderScreen


def test_day_trader_panels_exist():
    screen = DayTraderScreen()
    assert screen.market_panel.id == "market_overview"
    assert screen.orderbook_panel.id == "orderbook"
    assert screen.whale_panel.id == "whale_trades"
    assert screen.liquidations_panel.id == "liquidations_feed"
    assert screen.funding_panel.id == "funding_rates"
    assert screen.positions_panel.id == "positions"


class _AlertAppStub:
    def __init__(self) -> None:
        self.alerts = []

    def is_alert_enabled(self, name: str) -> bool:
        return name == "anomaly_spikes"

    def emit_alert(self, **kwargs) -> None:
        self.alerts.append(kwargs)


def test_day_trader_anomaly_engine_emits_multiple_signal_types():
    screen = DayTraderScreen()
    app = _AlertAppStub()
    screen._app = app
    screen._state.watchlist = ["BTC"]
    screen._state.price_history["BTC"] = [100.0, 100.0, 100.0, 100.0, 106.0]
    screen._state.volume_history["BTC"] = [10.0, 10.0, 10.0, 10.0, 40.0]
    screen._state.funding_history["BTC"] = [0.0, 0.0, 0.00012]
    screen._state.oi_history["BTC"] = [100.0, 100.0, 100.0, 100.0, 130.0]

    screen._check_anomalies()

    kinds = {a["payload"]["kind"] for a in app.alerts}
    assert "price_spike" in kinds
    assert "volume_surge" in kinds
    assert "funding_extreme" in kinds
    assert "oi_spike" in kinds


def test_day_trader_symbol_threshold_override_suppresses_alerts():
    screen = DayTraderScreen()
    app = _AlertAppStub()
    screen._app = app
    screen._state.watchlist = ["BTC"]
    screen._state.price_history["BTC"] = [100.0, 100.0, 100.0, 100.0, 106.0]
    screen._state.volume_history["BTC"] = [10.0, 10.0, 10.0, 10.0, 40.0]
    screen._state.funding_history["BTC"] = [0.0, 0.0, 0.00012]
    screen._state.oi_history["BTC"] = [100.0, 100.0, 100.0, 100.0, 130.0]
    screen.set_anomaly_thresholds(
        "BTC",
        {
            "price_spike_pct": 0.20,
            "volume_surge_mult": 8.0,
            "funding_extreme_rate": 0.001,
            "oi_spike_pct": 0.60,
        },
    )

    screen._check_anomalies()
    assert app.alerts == []
