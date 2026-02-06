# AGENTS.md – Operational Commands

This document lists the commands that automated agents should use to interact with the TickerTape repository.  Keep it concise (~60 lines).  All commands operate in the repository root.

## Playbooks

Use the institutional playbooks for implementation and review:

- `playbooks/backend_quant_engineer.md`
- `playbooks/frontend_tui_architect.md`
- `playbooks/research_reviewer.md`
- `playbooks/privacy_security_auditor.md`

## Installation

```bash
# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Optional: if using Poetry
# poetry install
```

## Running the Application

```bash
# Launch the TUI application
python -m tui.app

# or, if packaged as a CLI entry point
TickerTape
TTape
```

## Running Tests

```bash
# Run all unit tests
pytest -q

# Run a specific group of tests (e.g., validators)
pytest -q tests/validators

# Backtest smoke test (ensures engines run)
pytest -q -k backtest
```

## Linting & Formatting

```bash
# Run Ruff (combined lint & formatting)
ruff check .
ruff format .

# Alternatively, use separate tools
flake8 .
black --check .
isort --check-only .
```

## Type Checking

```bash
# Run mypy to check type hints
mypy --config-file mypy.ini .
```

## Backtest Smoke Test

```bash
# Run a minimal backtest from the CLI to verify core functionality
python -m tui.app backtest --data sample.csv --strategy simple

# Verify Monte Carlo runs
python -m tui.app mc --data sample.csv --strategy simple --runs 100
```

## Other Utilities

```bash
# Export logs from the current session
python -m tui.app export --logs

# Diagnose provider connectivity
python -m tui.app diagnose provider

# Validate a dataset snapshot
python -m tui.app validate ticks.csv
```

Ensure to run these commands after each task implementation to validate correctness.  If any command fails, fix the underlying issue before proceeding to the next task.
