import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.validation import extract_rows, run_validation, summarize_reports


def test_extract_rows_from_snapshot():
    snapshot = {"rows": [{"ts": 1, "symbol": "BTC"}]}
    rows = extract_rows(snapshot)
    assert rows == [{"ts": 1, "symbol": "BTC"}]


def test_summarize_reports_counts():
    rows = [{"ts": 1, "symbol": "BTC"}]
    reports = run_validation(rows)
    summary = summarize_reports(reports)
    assert "total_errors" in summary
    assert "total_warnings" in summary
    assert "by_validator" in summary
