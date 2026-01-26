# Secrets & API Key Setup

TickerTape never ships secrets in the repo. Configure your MoonDev API key locally.

## Required environment variables
- `MOONDEV_API_KEY` (preferred)

## Config file locations (outside repo)
TickerTape resolves the key in this order:
1. `MOONDEV_API_KEY` environment variable
2. Config file path (override with `TICKERTAPE_CONFIG_PATH`)
3. Local `.env` for development only (gitignored)

Default config file paths:
- **Linux**: `~/.config/tickertape/config.env`
- **macOS**: `~/Library/Application Support/TickerTape/config.env`
- **Windows**: `%APPDATA%\\TickerTape\\config.env`

**Config file format**
```
MOONDEV_API_KEY=your_key_here
```

## Security rules
- **Never commit keys** to the repo.
- **Never paste keys** into logs or screenshots.
- Use `TICKERTAPE_CONFIG_PATH` to point at a secure local file.
- `.env` is supported for dev only and is gitignored.

## Quick verification
1. Set the key:
   - `export MOONDEV_API_KEY="..."` (Linux/macOS)
   - `setx MOONDEV_API_KEY "..."` (Windows PowerShell)
2. Start the TUI.
3. If the key is missing, run `/secrets` or `/configure` to see setup guidance.
