"""
tests/kpi/test_cagr.py — Sprint 2, Day 10 deliverable
Run with: pytest tests/kpi/test_cagr.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "analytics"))
from cagr import cagr, compute_windowed_cagr, compute_all_windows  # noqa: E402


def test_cagr_normal_positive_growth():
    value, flag = cagr(100, 200, 5)
    assert flag is None
    assert round(value, 2) == 14.87

def test_cagr_normal_decline_but_still_positive():
    value, flag = cagr(200, 100, 5)
    assert flag is None
    assert value < 0

def test_cagr_decline_to_loss_flag():
    value, flag = cagr(100, -50, 3)
    assert value is None
    assert flag == "DECLINE_TO_LOSS"

def test_cagr_turnaround_flag():
    value, flag = cagr(-100, 50, 3)
    assert value is None
    assert flag == "TURNAROUND"

def test_cagr_both_negative_flag():
    value, flag = cagr(-100, -50, 3)
    assert value is None
    assert flag == "BOTH_NEGATIVE"

def test_cagr_zero_base_flag():
    value, flag = cagr(0, 100, 3)
    assert value is None
    assert flag == "ZERO_BASE"

def test_cagr_insufficient_data_start_missing():
    value, flag = cagr(None, 100, 3)
    assert value is None
    assert flag == "INSUFFICIENT"

def test_cagr_insufficient_data_end_missing():
    value, flag = cagr(100, None, 3)
    assert value is None
    assert flag == "INSUFFICIENT"

def test_windowed_cagr_missing_start_year_is_insufficient():
    value, flag = compute_windowed_cagr({2024: 100}, 2024, 5)
    assert value is None
    assert flag == "INSUFFICIENT"

def test_windowed_cagr_normal_case():
    value, flag = compute_windowed_cagr({2019: 100, 2024: 200}, 2024, 5)
    assert flag is None
    assert round(value, 2) == 14.87

def test_compute_all_windows_returns_expected_keys():
    result = compute_all_windows({2019: 100, 2021: 150, 2024: 200}, 2024, windows=(3, 5))
    assert set(result.keys()) == {"cagr_3yr", "cagr_3yr_flag", "cagr_5yr", "cagr_5yr_flag"}

def test_compute_all_windows_partial_data_flags_insufficient_for_missing_window():
    result = compute_all_windows({2019: 100, 2024: 200}, 2024, windows=(3, 5, 10))
    assert result["cagr_5yr_flag"] is None
    assert result["cagr_3yr_flag"] == "INSUFFICIENT"
    assert result["cagr_10yr_flag"] == "INSUFFICIENT"
