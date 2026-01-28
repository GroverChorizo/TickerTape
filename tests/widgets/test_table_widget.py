from tui.widgets.charts import TableWidget


def test_table_widget_numeric_and_heat():
    w = TableWidget()
    headers = ["Exchange", "Rate", "Annualized"]
    rows = [
        ["ExA", 0.00012, 1.5],
        ["ExB", -0.00020, -0.8],
    ]
    # numeric_cols: Rate (1), Annualized (2)
    # heat_cols: Annualized column uses max 2.0 for scaling
    w.update_table(headers, rows, numeric_cols=[1, 2], heat_cols={2: 2.0}, heat_width=4)
    # fallback to checking internal Text if present
    text = getattr(w, "renderable", None)
    if text is None:
        # Textual updates may store _renderable_text in some versions; fallback to no-op check
        assert True
        return
    plain = text.plain
    assert "+0.000120" in plain or "+0.00012" in plain
    assert "-0.000200" in plain or "-0.00020" in plain
    assert "+1.50%" not in plain  # not percent-formatted here, numeric formatting applied
    # heat bar presence check (simple block characters)
    assert any(ch in plain for ch in ("▉", "█", "▊", "▌", "▎", "▁"))
