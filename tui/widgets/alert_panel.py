"""Alert history panel with category filtering.

Used as the ``AlertSidebarSection`` inside the sidebar container and exposed as
the backward-compatible ``AlertPanel`` alias for any existing callers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from rich.text import Text
from textual.widgets import Static

from tui.state.alerts import AlertStore
from tui.themes.palettes import Palette, cypherpunk_default
from tickertape.core.alerts import AlertEvent, AlertSeverity


# ── category mapping ──────────────────────────────────────────────────────────

CATEGORIES = ("ALL", "WHALE", "FUNDING", "LIQUIDATION", "ANOMALY", "SYSTEM")

_CAT_KEYS: Dict[str, str] = {
    "whale": "WHALE",
    "wallet": "WHALE",
    "smart_money": "WHALE",
    "large_trade": "WHALE",
    "funding": "FUNDING",
    "arb": "FUNDING",
    "arbitrage": "FUNDING",
    "spread": "FUNDING",
    "extreme": "FUNDING",
    "liquidation": "LIQUIDATION",
    "cascade": "LIQUIDATION",
    "liq": "LIQUIDATION",
    "anomaly": "ANOMALY",
    "spike": "ANOMALY",
    "surge": "ANOMALY",
    "oi_": "ANOMALY",
}

_CAT_SHORT: Dict[str, str] = {
    "WHALE": "WHAL",
    "FUNDING": "FUND",
    "LIQUIDATION": "LIQ ",
    "ANOMALY": "ANOM",
    "SYSTEM": "SYS ",
}

_SEVERITY_ATTR = {
    AlertSeverity.CRITICAL: "red",
    AlertSeverity.WARNING: "orange",
    AlertSeverity.INFO: "cyan",
}


def categorize_alert(alert: AlertEvent) -> str:
    """Return the display category for an alert based on its type string."""
    t = alert.alert_type.lower()
    for key, cat in _CAT_KEYS.items():
        if key in t:
            return cat
    return "SYSTEM"


# ── main widget ───────────────────────────────────────────────────────────────

class AlertSidebarSection(Static):
    """Scrollable, categorized alert history for the left sidebar column.

    Renders as plain Rich ``Text`` — no border, compact-mode aware.
    Updates are triggered by calling ``refresh_panel()`` (called by the
    parent ``SidebarContainer`` on every status tick).
    """

    def __init__(self, store: AlertStore | None = None, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._store: AlertStore = store or AlertStore()
        self._active_category: str = "ALL"
        self._compact: bool = False
        self._palette: Palette = cypherpunk_default

    # ── public interface ──────────────────────────────────────────────────────

    def set_store(self, store: AlertStore) -> None:
        """Hot-swap the alert store (called when app.alert_store is available)."""
        self._store = store
        self.refresh_panel()

    def set_category(self, category: str) -> None:
        cat = category.upper()
        if cat in CATEGORIES:
            self._active_category = cat
            self.refresh_panel()

    def next_category(self) -> str:
        """Cycle to the next category; return its name."""
        idx = CATEGORIES.index(self._active_category)
        self._active_category = CATEGORIES[(idx + 1) % len(CATEGORIES)]
        self.refresh_panel()
        return self._active_category

    def set_compact(self, compact: bool) -> None:
        self._compact = compact
        self.refresh_panel()

    def set_palette(self, palette: Palette) -> None:
        self._palette = palette
        try:
            self.styles.background = palette.bg.panel
            self.styles.color = palette.text.primary
        except Exception:
            pass
        self.refresh_panel()

    def refresh_panel(self) -> None:
        self.update(self._build())

    # ── rendering ─────────────────────────────────────────────────────────────

    def _build(self) -> Text:
        p = self._palette
        text = Text()

        # Compact mode: just show a count badge
        if self._compact:
            n = len(self._store.alerts)
            style = f"bold {p.accent.red}" if n else p.text.muted
            text.append(f"!{n}", style=style)
            return text

        # Section header
        text.append("ALERTS", style=f"bold {p.accent.purple}")
        if self._store.muted:
            text.append("  [muted]", style=p.text.muted)
        text.append("\n")

        # Category selector — abbreviated 4-char labels
        parts: List[str] = [
            f"[{c[:4]}]" if c == self._active_category else c[:4]
            for c in CATEGORIES
        ]
        text.append("  ".join(parts) + "\n", style=p.text.muted)
        text.append("─" * 18 + "\n", style=p.border.panel)

        # Filter to active category
        alerts = list(self._store.alerts)
        if self._active_category != "ALL":
            alerts = [a for a in alerts if categorize_alert(a) == self._active_category]

        if not alerts:
            text.append("No alerts.", style=p.text.muted)
            return text

        # Render newest-first, capped at 10
        for alert in reversed(alerts[-10:]):
            ts = datetime.fromtimestamp(alert.timestamp_ms / 1000, tz=timezone.utc)
            attr = _SEVERITY_ATTR.get(alert.severity, "cyan")
            color = getattr(p.accent, attr, p.text.primary)
            cat = categorize_alert(alert)
            label = _CAT_SHORT.get(cat, "    ")
            text.append(f"{ts.strftime('%H:%M')} ", style=p.text.muted)
            text.append(f"{label} ", style=f"bold {color}")
            atype = alert.alert_type.replace("_", " ").title()
            text.append(f"{atype[:13]}\n", style=color)

        return text


# ── backward-compatible alias ─────────────────────────────────────────────────

class AlertPanel(AlertSidebarSection):
    """Thin alias kept for any existing imports of ``AlertPanel``."""

    def __init__(self, store: AlertStore, **kwargs) -> None:
        # Accept legacy panel_id kwarg from PanelBase-style callers
        if "panel_id" in kwargs:
            kwargs.setdefault("id", kwargs.pop("panel_id"))
        super().__init__(store=store, **kwargs)
