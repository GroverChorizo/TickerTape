# Navigation Carousel & Breadcrumb Specification

## Purpose

Provide an intuitive mechanism for users to manage and navigate between multiple open screens or panels within TickerTape.  As users open detached panels or additional profile windows, the carousel keeps track of active screens and allows rapid switching without losing context.

## Functional Requirements

* **Carousel Component** – Implement a carousel UI element that lists all currently open screens and panels.  The carousel should display each entry’s title, an optional icon and a position indicator (e.g., “2 of 5”).
* **Keyboard Navigation** – Allow users to cycle through open entries using keyboard shortcuts (e.g., `Ctrl+Tab` for next, `Shift+Ctrl+Tab` for previous).  Provide additional commands to jump directly to a specific entry (`:goto <n>`).
* **Breadcrumb Trail** – Display a breadcrumb or status indicator showing the current position in the carousel and the total number of open screens.  The breadcrumb should appear in the status bar or header without consuming excessive space.
* **Integration with Detached Panels** – Include detached panels (opened via `--panel <name>`) in the carousel.  Switching should bring the selected window to the foreground in the terminal multiplexer or operating system.
* **Persistence of Order** – Maintain the order of entries across sessions.  When the user restarts the application, reopen previously active screens (subject to environment and data availability) and restore the carousel order.
* **Commands** – Add commands to list open screens (`:tabs`), close a screen (`:close <n>`), rename a screen (`:rename <n> <new name>`) and toggle the carousel view on/off.  Provide context‑aware help in the command palette.

## Non‑Functional Requirements

* **Performance** – Navigating between entries should be instantaneous and not interrupt streaming data or background tasks.
* **Scalability** – Support at least 10–12 open screens without degrading performance.  Consider lazy rendering or grouping entries if the list grows large.
* **Visual Consistency** – Match the aesthetic of the rest of the TUI (dark themes, rounded corners, accent colours).  The carousel should be unobtrusive until invoked.

## Implementation Notes

* Implement the carousel as a dedicated component in `tui/ui/tab_carousel.py` and surface breadcrumb/status text via `tui/ui/status_bar.py`.
* Track open screens and keyboard navigation inside `tui/app.py` (no separate NavigationManager).
* Persist the open-screen order in the UI cache (`data/ui_cache.json`) and reload it on startup.
* Unit tests should cover cycling operations, persistence and error handling (e.g., closing a screen when only one remains).
