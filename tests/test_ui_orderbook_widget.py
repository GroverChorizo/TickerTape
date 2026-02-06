from tui.ui.widgets.orderbook_imbalance import OrderbookImbalanceWidget


def test_orderbook_widget_renders_basic_bars():
    w = OrderbookImbalanceWidget()
    payload = {
        "symbol": "BTC",
        "bids": [[43000.0, 1.0], [42950.0, 2.0]],
        "asks": [[43010.0, 0.5], [43020.0, 0.2]],
    }
    w.update_from_orderbook(payload)
    panel = w.render()
    assert hasattr(panel, "title") and "Orderbook Imbalance" in (panel.title or "")
    # render the panel to text via a Console to verify visual content
    from rich.console import Console

    console = Console(record=True, width=80)
    console.print(panel)
    out = console.export_text()
    assert "best bid" in out.lower()
    assert "43000" in out
    # imbalance should show bids/asks labels
    assert "Bids" in out and "Asks" in out
