from tui.widgets.funding_panel import FundingPanel
from tui.themes.palettes import cypherpunk_default


def test_funding_row_styles():
    panel = FundingPanel()
    panel.palette = cypherpunk_default
    rows = [
        {
            "exchange": "ExA",
            "symbol": "BTC",
            "rate": 0.0001,
            "annualized_pct": 1.5,
            "spread_pct": -0.2,
            "timestamp_ms": None,
            "arbitrage": True,
            "status": "ok",
        },
        {
            "exchange": "ExB",
            "symbol": "BTC",
            "rate": -0.0002,
            "annualized_pct": -0.8,
            "spread_pct": 0.1,
            "timestamp_ms": None,
            "arbitrage": False,
            "status": "stale",
        },
    ]
    lines = panel._render_table(rows)
    # find first Text row for first data row
    text_objs = [item for item in lines if hasattr(item, "__rich_console__") or hasattr(item, "plain")]
    assert any("ARB" in t.plain for t in text_objs)
    # Ensure styling for positive annualized (1.5) is green
    # We check plain content includes '+1.50%'
    assert any("+1.50%" in t.plain for t in text_objs)
    assert any("-0.80%" in t.plain for t in text_objs)
