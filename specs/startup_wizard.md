# Startup Wizard Specification

## Purpose

Provide a first‑time onboarding flow that guides users through selecting their trading profile, choosing a theme, configuring their dashboard and setting up alerts.  The wizard ensures a tailored experience from the moment the terminal is launched.

## Functional Requirements

* **Welcome Screen** – The wizard begins with a welcome message and explains that it will guide users through profile selection, theme choice, data stream configuration and alert setup【438442747367044†L1431-L1450】.  Users can continue or skip the wizard.
* **Profile Selection** – Screen 2 allows the user to choose among Day Trader, Liquidation Hunter, Whale Watcher, Funding Arbitrageur or create a custom profile.  A visible cursor (`▶`) moves with arrow keys and highlights the current selection【438442747367044†L1454-L1485】.
* **Theme Selection** – Screen 3 presents the available themes (cypherpunk, Dark Pro, Matrix, Minimal) with previews.  Users can press `P` to preview a theme in full screen【438442747367044†L1488-L1511】.
* **Dashboard Customization** – Screen 4 lists the default panels for the selected profile and lets users toggle additional panels (Funding Rates, Orderbook Depth, AI Assistant, Backtest Results) using the space bar【438442747367044†L1514-L1534】.
* **Alerts Configuration** – Screen 5 lets users enable alerts for whale trades, liquidation cascades, extreme funding rates and other conditions.  They choose the notification method (visual, audio, both)【438442747367044†L1537-L1557】.
* **Completion** – Screen 6 summarises the selected profile, theme, panels and alerts.  Configuration is saved and applied automatically on subsequent launches【438442747367044†L1561-L1583】.
* **Persistence** – Wizard selections must be stored in a local configuration file.  Users can access the Settings panel (Ctrl+,) later to modify preferences【438442747367044†L1561-L1583】.

## Non‑Functional Requirements

* **Skippable** – Users may skip the wizard and use default settings.  The wizard should never block access to the application.
* **Resumable** – If the wizard is interrupted, progress should be saved and resumed on next start.
* **Accessibility** – The wizard must be keyboard‑navigable with clear focus indicators and instructions【438442747367044†L1454-L1485】.

## Implementation Notes

* Implement the wizard as a multi‑step form in `ui/wizard.py` using Textual’s `Screen` class.  Each step is a separate `Container` with navigation buttons.
* Use a state machine to manage progress between steps and store selections.
* On completion, write settings to `~/.ticker_tape/config.yaml` (or similar).  Provide functions to load these preferences at startup.
