"""
src/analytics/cashflow_kpis.py — Sprint 2, Day 11 deliverable
Cash-flow-based KPIs and the 8-pattern capital allocation classifier.
"""
from typing import Optional, List, Tuple


def free_cash_flow(cash_from_operations: float, cash_from_investing: float) -> float:
    """FCF = CFO + CFI. Negative values are allowed and meaningful."""
    return round((cash_from_operations or 0) + (cash_from_investing or 0), 4)


def cfo_quality_score(cfo_series: List[float], pat_series: List[float]) -> Tuple[Optional[float], Optional[str]]:
    """
    CFO Quality Score = average(CFO / PAT) over up to the last 5 years.
    Returns (ratio, label):
      ratio > 1.0        -> "High Quality"
      0.5 <= ratio <= 1.0 -> "Moderate"
      ratio < 0.5         -> "Accrual Risk"
    Returns (None, None) if there's no usable PAT data (all zero/empty).
    """
    pairs = [(c, p) for c, p in zip(cfo_series[-5:], pat_series[-5:])
             if c is not None and p is not None and p != 0]
    if not pairs:
        return None, None

    ratios = [c / p for c, p in pairs]
    avg_ratio = round(sum(ratios) / len(ratios), 4)

    if avg_ratio > 1.0:
        label = "High Quality"
    elif avg_ratio >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return avg_ratio, label


def capex_intensity(cash_from_investing: float, sales: float) -> Tuple[Optional[float], Optional[str]]:
    """
    CapEx Intensity % = abs(cash_from_investing) / sales * 100
      < 3%   -> "Asset Light"
      3-8%   -> "Moderate"
      > 8%   -> "Capital Intensive"
    """
    if sales in (0, None) or sales == 0:
        return None, None
    intensity = round(abs(cash_from_investing or 0) / sales * 100, 4)
    if intensity < 3:
        label = "Asset Light"
    elif intensity <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"
    return intensity, label


def fcf_conversion_rate(fcf: float, operating_profit: float) -> Optional[float]:
    """FCF Conversion Rate % = FCF / operating_profit * 100."""
    if operating_profit in (0, None) or operating_profit == 0:
        return None
    return round((fcf / operating_profit) * 100, 4)


def capital_allocation_pattern(cfo: float, cfi: float, cff: float,
                                cfo_pat_ratio: Optional[float] = None,
                                shareholder_return_threshold: float = 1.2) -> str:
    """
    Classifies a company-year into one of 8 capital-allocation patterns based
    on the sign of (CFO, CFI, CFF), matching the sprint's pattern table:

      (+,-,-)                       -> "Reinvestor"
      (+,-,-) with high CFO/PAT     -> "Shareholder Returns"
      (+,+,-)                       -> "Liquidating Assets"
      (-,+,+)                       -> "Distress Signal"
      (-,-,+)                       -> "Growth Funded by Debt"
      (+,+,+)                       -> "Cash Accumulator"
      (-,-,-)                       -> "Pre-Revenue"
      (+,-,+)                       -> "Mixed"

    The (+,-,-) case is disambiguated using cfo_pat_ratio: values at or above
    `shareholder_return_threshold` (default 1.2x, i.e. CFO comfortably
    exceeds PAT with room to fund both reinvestment and payouts) are labeled
    "Shareholder Returns"; otherwise "Reinvestor".
    """
    def sign(x):
        return "+" if (x or 0) >= 0 else "-"

    pattern = (sign(cfo), sign(cfi), sign(cff))

    if pattern == ("+", "-", "-"):
        if cfo_pat_ratio is not None and cfo_pat_ratio >= shareholder_return_threshold:
            return "Shareholder Returns"
        return "Reinvestor"
    if pattern == ("+", "+", "-"):
        return "Liquidating Assets"
    if pattern == ("-", "+", "+"):
        return "Distress Signal"
    if pattern == ("-", "-", "+"):
        return "Growth Funded by Debt"
    if pattern == ("+", "+", "+"):
        return "Cash Accumulator"
    if pattern == ("-", "-", "-"):
        return "Pre-Revenue"
    if pattern == ("+", "-", "+"):
        return "Mixed"
    # remaining combination: (-,+,-) has no defined label in the spec
    return "Unclassified"
