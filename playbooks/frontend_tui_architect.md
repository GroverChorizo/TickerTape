# Frontend TUI Architect Playbook

## Purpose
Deliver a responsive, high-density Textual TUI that matches the institutional visual language and remains keyboard-first.

## Guardrails
- No financial advice or trade recommendations.
- Local-only operation; never transmit user data.
- Avoid synthetic data in production views.
- Preserve theme system and profile separation.

## Workflow
1. Confirm UI requirements in `FtheVision_v1_5_5.txt` and `specs/ui_layout.md`.
2. Build small, composable widgets; prefer reuse over duplication.
3. Ensure layout adapts across breakpoints with no content loss.
4. Add tests for rendering, focus, and resizing behavior.

## UI Checklist
- Profile screens are separate, not just filtered views.
- Command palette accessible via `/` or `Ctrl+K`.
- Sidebar, tab bar, and carousel behave per breakpoints.
- Fullscreen and density toggles persist per session.
- Alerts are visible and non-blocking.

## Testing Checklist
- Snapshot tests for key panels.
- Keyboard navigation tests.
- Layout tests across width breakpoints.

