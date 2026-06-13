# Secrets & API Key Setup

TickerTape never ships secrets in the repo. Configure your API key locally.

The core feeds are **keyless** (Hyperliquid info API / ccxt). The only thing
that needs a key is the **opt-in "MoonDev Data" console** (`:moondev`) — a
secondary, daily-cadence page over the external data layer. Without a key, the
app runs normally and that page shows a "not configured" notice.

## Canonical secrets file (outside repo)
TickerTape reads API keys from a single `.env` file:
- **Linux/macOS**: `~/.tickertape/secrets/HLdontShare.env`
- **Windows**: `%USERPROFILE%\\.tickertape\\secrets\\HLdontShare.env`

You can override the path with:
- `TICKERTAPE_SECRETS_PATH`
- `HL_DONT_SHARE_PATH`

**Secrets file format**
```
MOONDEV_API_KEY=your_key_here
# optional — override the data-layer base URL (defaults to the standard host):
# DATALAYER_BASE_URL=https://api.moondev.com
```
The base URL can also be set in `config.env` as `datalayer_base_url` or via the
`TICKERTAPE_DATALAYER_BASE_URL` environment variable.

## Security rules
- **Never commit keys** to the repo.
- **Never paste keys** into logs or screenshots.
- Keep `HLdontShare.env` outside the repo and private.

## Quick verification
1. Set `MOONDEV_API_KEY` in `HLdontShare.env`.
2. Start the TUI.
3. If the key is missing, run `/secrets` to open the file.
