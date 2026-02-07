# Secrets & API Key Setup

TickerTape never ships secrets in the repo. Configure your MoonDev API key locally.

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
```

## Security rules
- **Never commit keys** to the repo.
- **Never paste keys** into logs or screenshots.
- Keep `HLdontShare.env` outside the repo and private.

## Quick verification
1. Set `MOONDEV_API_KEY` in `HLdontShare.env`.
2. Start the TUI.
3. If the key is missing, run `/secrets` to open the file.
