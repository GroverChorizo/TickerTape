# Secrets File Specification

## Purpose

Define the standard for managing API keys and other sensitive credentials used by TickerTape.  A consistent secrets file allows the application to load authentication details without hard‑coding them in source code or relying on environment variables alone.

## Requirements

* **Default Path** – The application must look for a secrets file at `~/.ticker_tape/secrets.yaml` when it starts.  If this file does not exist, the app should create it with placeholder keys and inform the user of its location.
* **Override** – Users may override the default path by setting an environment variable (e.g., `TICKER_TAPE_SECRETS_PATH`) or specifying a command‑line argument (`--secrets <path>`).  The app should prioritise explicit arguments over environment variables and fall back to the default location.
* **File Format** – Use YAML for readability.  Each API or service key should have a descriptive field (e.g., `hyperliquid_api_key`, `exchange_api_secret`).  Include comments explaining the purpose of each key.
* **Security** – The secrets file must not be checked into version control.  Document this in `.gitignore` and in onboarding instructions.  The file should have restricted permissions (`600`) on Unix systems to prevent other users from reading it.
* **CLI Integration** – Provide a command (`:secrets`) that prints the current secrets file path and opens it in the user’s default editor.  The command should also display a warning if the file is missing or has insecure permissions.
* **Wizard Support** – During the startup wizard, prompt the user to locate or create the secrets file.  Offer to create the file at the default location if none is provided.
* **User Awareness** – After creating the file, the application must log the path to the console (and optionally display a non‑blocking pop‑up) so users know where to insert their API keys.

## Implementation Notes

* Implement secrets handling in a dedicated module (`config/secrets.py`).  Provide functions to resolve the secrets path, create the file with placeholders, read key values and set file permissions.
* Update the startup sequence to call this module before connecting to any external APIs.
* Provide unit tests that simulate missing files, override paths and permission errors.
* Document the secrets file format in the README and in the startup wizard.