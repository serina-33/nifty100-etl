"""
src/analytics/cagr.py — Sprint 2, Day 10 deliverable
CAGR engine handling all 6 required edge cases. Every function returns a
(value, flag) tuple: value is None whenever the CAGR isn't mathematically
meaningful, and flag explains WHY, so downstream consumers never have to
guess whether a None means "no data" or "declined to a loss".
"""
from typing import Optional, Tuple

FLAG_DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
FLAG_TURNAROUND = "TURNAROUND"
FLAG_BOTH_NEGATIVE = "BOTH_NEGATIVE"
FLAG_ZERO_BASE = "ZERO_BASE"
FLAG_INSUFFICIENT = "INSUFFICIENT"


def cagr(start: Optional[float], end: Optional[float], n_years: int) -> Tuple[Optional[float], Optional[str]]:
    """
    CAGR % = ((end / start) ** (1 / n) - 1) * 100

    Edge cases (in priority order):
      - fewer than n_years of usable data (start/end is None) -> (None, INSUFFICIENT)
      - start == 0                                             -> (None, ZERO_BASE)
      - start > 0 and end > 0                                  -> normal computation
      - start > 0 and end < 0  (profit -> loss)                -> (None, DECLINE_TO_LOSS)
      - start < 0 and end > 0  (loss -> profit)                -> (None, TURNAROUND)
      - start < 0 and end < 0  (loss throughout)               -> (None, BOTH_NEGATIVE)
    """
    if start is None or end is None or n_years is None or n_years <= 0:
        return None, FLAG_INSUFFICIENT

    if start == 0:
        return None, FLAG_ZERO_BASE

    if start > 0 and end > 0:
        value = ((end / start) ** (1 / n_years) - 1) * 100
        return round(value, 4), None

    if start > 0 and end < 0:
        return None, FLAG_DECLINE_TO_LOSS

    if start < 0 and end > 0:
        return None, FLAG_TURNAROUND

    if start < 0 and end < 0:
        return None, FLAG_BOTH_NEGATIVE

    # start > 0 and end == 0, or other unhandled zero-crossing edge case
    return None, FLAG_ZERO_BASE


def compute_windowed_cagr(yearly_values: dict, as_of_year: int, window: int) -> Tuple[Optional[float], Optional[str]]:
    """
    Computes CAGR over a window of `window` years ending at as_of_year, given
    a dict of {year: value}. Looks up the start year (as_of_year - window) and
    end year (as_of_year); if either year is missing from yearly_values, this
    is treated as insufficient data.

    Example: compute_windowed_cagr({2019: 100, 2024: 200}, 2024, 5) -> (14.87, None)
    """
    start_year = as_of_year - window
    if start_year not in yearly_values or as_of_year not in yearly_values:
        return None, FLAG_INSUFFICIENT
    return cagr(yearly_values[start_year], yearly_values[as_of_year], window)


def compute_all_windows(yearly_values: dict, as_of_year: int,
                         windows=(3, 5, 10)) -> dict:
    """
    Convenience wrapper: computes CAGR for every requested window and returns
    a flat dict like:
      {"cagr_3yr": 12.3, "cagr_3yr_flag": None,
       "cagr_5yr": None,  "cagr_5yr_flag": "INSUFFICIENT", ...}
    """
    result = {}
    for w in windows:
        value, flag = compute_windowed_cagr(yearly_values, as_of_year, w)
        result[f"cagr_{w}yr"] = value
        result[f"cagr_{w}yr_flag"] = flag
    return result
