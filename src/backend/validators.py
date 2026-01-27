"""Small validators and guardrails for research integrity.

- include an anti-lookahead guard: ensure signals are timestamped before the bar they will be executed on
"""

from __future__ import annotations
from datetime import datetime
from typing import Iterable


def ensure_signal_before_execution(
    signal_time: datetime, execution_time: datetime
) -> None:
    """Ensure the signal_time occurs strictly before the execution_time.

    Raises ValueError if signal_time >= execution_time
    """
    if signal_time >= execution_time:
        raise ValueError(
            "Signal timestamp must be strictly before execution time to prevent lookahead bias"
        )


def batch_validate_signals(
    signals: Iterable[datetime], execution_time: datetime
) -> None:
    for s in signals:
        ensure_signal_before_execution(s, execution_time)
