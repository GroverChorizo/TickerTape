import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

textual = pytest.importorskip("textual")

from tui.widgets.panel_base import PanelBase
from tui.widgets.charts import (
    BarChartWidget,
    HeatmapWidget,
    SparklineWidget,
    TableWidget,
)


def test_panel_focus_and_alert_state():
    panel = PanelBase(panel_id="test", title="Test")
    panel.set_focus(True)
    assert panel._focused is True
    panel.set_alert(True)
    assert panel._alert is True
    panel.clear_alert()
    assert panel._alert is False


def test_chart_widgets_render():
    spark = SparklineWidget()
    spark.update_series([1, 2, 3], label="BTC")
    assert "BTC" in str(spark.renderable)

    heat = HeatmapWidget()
    heat.update_pairs([("BTC", 10.0), ("ETH", 5.0)])
    assert "BTC" in str(heat.renderable)

    bars = BarChartWidget()
    bars.update_bars([("buy", 3.0), ("sell", 1.0)])
    assert "buy" in str(bars.renderable)

    table = TableWidget()
    table.update_table(["A", "B"], [["1", "2"]])
    assert "A | B" in str(table.renderable)
