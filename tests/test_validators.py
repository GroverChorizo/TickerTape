import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
import pytest
from datetime import datetime, timedelta, timezone
from backend.validators import ensure_signal_before_execution, batch_validate_signals


def test_ensure_signal_before_execution_passes():
    now = datetime.now(timezone.utc)
    signal = now
    execution = now + timedelta(seconds=60)
    # should not raise
    ensure_signal_before_execution(signal, execution)


def test_ensure_signal_before_execution_fails():
    now = datetime.now(timezone.utc)
    signal = now
    execution = now
    with pytest.raises(ValueError):
        ensure_signal_before_execution(signal, execution)


def test_batch_validate_signals():
    now = datetime.now(timezone.utc)
    signals = [now - timedelta(seconds=10), now - timedelta(seconds=5)]
    execution = now
    batch_validate_signals(signals, execution)
    # invalid case
    with pytest.raises(ValueError):
        batch_validate_signals([now, now + timedelta(seconds=1)], now)
