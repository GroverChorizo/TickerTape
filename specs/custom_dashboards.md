# Panel Resizing & Custom Dashboards Specification

## Purpose

Enable users to tailor their TickerTape experience by resizing panels within a profile and constructing entirely new dashboards composed of their preferred panels and data feeds.  This specification extends the core layout system and profile architecture to support a truly modular interface.

## Functional Requirements

* **Interactive Panel Resizing** – Each panel must expose drag handles on its right and bottom edges (and corners) when the user hovers or presses a modifier key.  Dragging these handles should resize the panel within the constraints of the grid, allowing the user to allocate more space to important data and less to others.
* **Grid Awareness** – Resizing must update the underlying layout grid so that adjacent panels adjust seamlessly.  The layout manager should enforce minimum and maximum sizes to prevent accidental collapse or overflow.
* **Custom Dashboard Builder** – Provide an interface (accessible via the Settings screen or wizard) that lets users:
  1. Create a new profile from scratch.
  2. Choose from the library of available panels (charts, heatmaps, tables, lists, etc.).
  3. Arrange panels via drag‑and‑drop on a blank grid and resize them as desired.
  4. Assign a name and description to the custom dashboard.
  5. Save the dashboard to the configuration directory.
* **Persistent Layout** – Custom dashboards must be saved to `data/custom_dashboards.json` (under the configured data root). On application start, the system loads built‑in profiles as well as any custom dashboards defined by the user.
* **Reusable Layout Logic** – Resizing and arrangement logic should reuse the base layout manager (see `tui/ui/layout.py`) and not duplicate code.  Custom dashboards behave identically to built‑in profiles regarding breakpoints, themes, density and fullscreen modes.
* **Commands for Dashboard Management** – Implement commands to list (`:dashboards`), select (`:dashboard <name>`), edit (`:dashboard edit <name>`) and delete (`:dashboard delete <name>`) custom dashboards.  Provide contextual help in the command palette.
* **Validation & Error Handling** – Prevent duplicate names and notify the user if a dashboard cannot be saved or loaded.  Validate that selected panels exist and are compatible with each other (e.g., requiring a provider connection).

## Non‑Functional Requirements

* **Usability** – Resizing handles must be discoverable without cluttering the interface.  Use subtle icons or highlights to indicate that panels can be resized.  Provide tooltips or hints on first use.
* **Persistence** – Saving and loading dashboards must be fast and not block the UI.  Use asynchronous file I/O where appropriate.
* **Backwards Compatibility** – New versions of the dashboard format should be backward compatible.  Include a version field in the YAML definition and migrations if needed.
* **Security** – Dashboard definitions should not contain executable code.  Only store panel configuration, layout positions, sizes and user metadata.

## Implementation Notes

* Introduce a `Dashboard` model that encapsulates the layout grid, panel list and metadata.  Provide serialization to/from JSON.
* Extend the `Panel` base class to include resize hooks (on drag start, update, end).  Use Textual or Rich events for drag handling.
* The layout manager must recompute grid spans when panels change size.  Use fractional units or fixed cell counts per breakpoint.
* Unit tests should simulate dragging operations via programmatic events; verify that the resulting layout matches expectations and persists correctly.
