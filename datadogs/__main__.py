import sys

# Windows Task Scheduler runs us under a cp1252 console, which cannot encode
# the preflight's unicode (→, …). Force UTF-8 so a logging character can never
# crash a fetch.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from datadogs.cli import main  # noqa: E402

sys.exit(main())
