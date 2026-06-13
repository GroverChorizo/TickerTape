"""Serve the TickerTape Textual UI as a local desktop/web app.

This is the "desktop" packaging path chosen for the command center: keep the
Textual UI and serve it (via ``textual-serve``) so it runs in a browser window
instead of only a terminal. Launch with ``tickertape-serve`` or ``tt serve``.
"""

from __future__ import annotations

import os
import sys


def run(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Allow `tt serve [host] [port]` and `tickertape-serve [host] [port]`.
    if argv and argv[0] == "serve":
        argv = argv[1:]
    host = os.environ.get("TICKERTAPE_SERVE_HOST", "127.0.0.1")
    port = int(os.environ.get("TICKERTAPE_SERVE_PORT", "8000"))
    if argv:
        host = argv[0]
    if len(argv) > 1:
        try:
            port = int(argv[1])
        except ValueError:
            pass

    try:
        from textual_serve.server import Server
    except ImportError:
        sys.stderr.write(
            "textual-serve is not installed.\n"
            "  pip install textual-serve\n"
            "then run `tickertape-serve` (or `tt serve`).\n"
        )
        raise SystemExit(1)

    # Serve the exact same entry point the terminal uses.
    command = f"{sys.executable} -m tui.app"
    server = Server(command, host=host, port=port, title="TickerTape")
    sys.stderr.write(f"TickerTape serving at http://{host}:{port}  (Ctrl-C to stop)\n")
    server.serve()


if __name__ == "__main__":
    run()
