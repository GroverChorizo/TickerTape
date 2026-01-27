import os
import json
import urllib.request
import sys

PR = open("PR_DRAFT.md", "r", encoding="utf-8").read()
body = {
    "title": "Backend MVP — Snapshots, Alerts, Dataset Registry (Frontend-Ready)",
    "head": "feat/backend/mvp-snapshots-alerts",
    "base": "main",
    "body": PR,
    "draft": True,
}
TOKEN = os.environ.get("GHTOKEN")
if not TOKEN:
    print("Missing GHTOKEN env var", file=sys.stderr)
    sys.exit(2)
headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "TickerTape-Agent",
    "Authorization": "Bearer " + TOKEN,
}
req = urllib.request.Request(
    "https://api.github.com/repos/GroverChorizo/TickerTape/pulls",
    data=json.dumps(body).encode("utf-8"),
    headers=headers,
)
import urllib.error

try:
    with urllib.request.urlopen(req) as resp:
        out = resp.read().decode("utf-8")
        print(out)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8") if e.fp else ""
    print("HTTPError", e.code, e.reason)
    print("Body:", body)
    raise
