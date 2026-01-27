# User Interface & Layout Specification

## Purpose

Define the principles and requirements for the terminal user interface (TUI).  The layout must be responsive, information‑dense and visually coherent, following the cyber‑punk aesthetic described in theVision while remaining customizable for different profiles.

## Functional Requirements

* **Separate Screens per Profile** – Each trading profile (Day Trader, Liquidation Hunter, Whale Watcher, Funding Arbitrageur) must live on its own screen.  Do not implement a single screen with highlighted panels; switching profiles should change the entire view【438442747367044†L206-L216】.
* **Panel Layouts** – Provide multiple breakpoints for different terminal widths:
  - **Ultra‑Wide (>160 cols)** – Display all panels simultaneously in a grid【438442747367044†L553-L565】.
  - **Wide (120–160 cols)** – Show 4–6 panels in a grid; sidebar visible【438442747367044†L573-L589】.
  - **Standard (80–120 cols)** – Show a 2×2 grid with a collapsible sidebar【438442747367044†L590-L603】.
  - **Narrow (60–80 cols)** – Stack panels vertically with a tab bar【438442747367044†L614-L632】.
  - **Compact (<60 cols)** – Display a single panel and use a hamburger menu for navigation【438442747367044†L635-L659】.
* **Sidebar & Tabs** – Include a responsive sidebar for quick access to panels; collapse to icons only on narrow screens.  Provide a bottom tab bar for switching when panels are stacked【438442747367044†L614-L632】.
* **Fullscreen Mode** – Pressing `F` toggles the active panel into fullscreen, exposing additional detail (e.g., more order book levels, extended charts)【438442747367044†L685-L723】.
* **Detached Panels** – Allow power users to open panels in separate terminal windows using a CLI flag (e.g., `--panel orderbook`)【438442747367044†L751-L777】.
* **Density Modes** – Support “comfortable” and “compact” modes; pressing `D` toggles between them.  Comfortable mode adds padding while compact mode maximises data density【438442747367044†L929-L943】.
* **Keybindings & Navigation** – Follow the default keybindings specified in theVision (e.g., `/` or `Ctrl+K` for command palette, `Tab` to cycle panels)【438442747367044†L1298-L1340】.  Document reserved keys and conflict resolution.

## Non‑Functional Requirements

* **Performance** – UI updates must not block for more than 100 ms during typical usage; animations should be smooth.
* **Accessibility** – Support keyboard‑only navigation and provide clear focus indicators on active panels【438442747367044†L1400-L1405】.
* **Aesthetic Consistency** – Use the specified colour palette (cypherpunk default with accent colours for events) and styling guidelines (rounded corners, beveled borders)【438442747367044†L1394-L1395】.  The default background **must** be dark grey or black – avoid blue or other bright backgrounds.  Themes should provide high‑contrast text on dark backgrounds and allow the user to switch colours via the theme system.
* **Theming** – Allow users to switch between themes (cypherpunk, Dark Pro, Matrix, Minimal).  The theme selection is part of the startup wizard【438442747367044†L1490-L1511】.

## Implementation Notes

* Implement layout logic using Textual’s grid and container primitives.  Use CSS for borders, rounded corners and animations.
* Provide a `Panel` base class with focus and alert states; derive specific panels (e.g., Whale Feed) from it.
* Manage responsive behaviour via a breakpoints module that listens to terminal width changes and recomputes panel layouts.
* Keep the layout definitions in `ui/layout.py` and theme styles in `ui/themes/`.
