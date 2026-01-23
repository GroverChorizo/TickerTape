"""Structured JSON logging setup for backend modules.

- Uses a minimal JSON formatter with no sensitive payloads
- Imported by package __init__ to configure logging at import time
"""
from __future__ import annotations
import logging
import sys
import json
from typing import Any

logger = logging.getLogger("hyperliquid.backend")

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Build a minimal, sanitized log record
        obj: dict[str, Any] = {
            "level": record.levelname,
            "time": self.formatTime(record, self.datefmt),
            "msg": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        return json.dumps(obj, separators=(',', ':'))


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    # Avoid adding duplicate handlers when reimported
    if not logger.handlers:
        logger.addHandler(handler)
    logger.setLevel(level)


# Convenience function for other modules
def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name or "hyperliquid.backend")