"""
src/analytics/ratios.py — Sprint 2, Day 08-09 deliverable
Profitability, leverage, and efficiency ratio functions.

Every function returns None where the formula is mathematically undefined
(zero/negative denominators), rather than raising or returning a misleading
0 or infinity — the one deliberate exception is Debt-to-Equity, which
returns 0 (not None) when a company has zero borrowings, since "debt-free"
is a meaningful, well-defined value rather than an undefined one.
"""
from typing import Optional


# --------------------------- Day 08: Profitability ---------------------------

def net_profit_margin(net_profit: float, sales: float) -> Optional[float]:
    """Net Profit Margin % = net_profit / sales * 100."""
    if sales in (0, None) or sales == 0:
        return None
    return round((net_profit / sales) * 100, 4)


def operating_profit_margin(operating_profit: float, sales: float) -> Optional[float]:
    """Operating Profit Margin % = operating_profit / sales * 100."""
    if sales in (0, None) or sales == 0:
        return None
    return round((operating_profit / sales) * 100, 4)


def opm_cross_check(calculated_opm: Optional[float], reported_opm_pct: Optional[float],
                     tolerance_pp: float = 1.0) -> dict:
    """
    Cross-checks the calculated OPM against the source-reported opm_pct field.
    Returns a dict with the difference and whether it exceeds tolerance (in
    percentage points), so the caller can decide whether to log it.
    """
    if calculated_opm is None or reported_opm_pct is None:
        return {"diff_pp": None, "mismatch": False}
    diff = round(abs(calculated_opm - reported_opm_pct), 4)
    return {"diff_pp": diff, "mismatch": diff > tolerance_pp}


def return_on_equity(net_profit: float, equity_capital: float, reserves: float) -> Optional[float]:
    """ROE % = net_profit / (equity_capital + reserves) * 100."""
    denom = (equity_capital or 0) + (reserves or 0)
    if denom <= 0:
        return None
    return round((net_profit / denom) * 100, 4)


def return_on_capital_employed(ebit: float, equity_capital: float, reserves: float,
                                borrowings: float) -> Optional[float]:
    """ROCE % = EBIT / (equity_capital + reserves + borrowings) * 100."""
    denom = (equity_capital or 0) + (reserves or 0) + (borrowings or 0)
    if denom <= 0:
        return None
    return round((ebit / denom) * 100, 4)


def roce_benchmark_check(roce_pct: Optional[float], is_financials_sector: bool,
                          absolute_threshold: float = 15.0,
                          sector_relative_benchmark: Optional[float] = None) -> Optional[bool]:
    """
    Returns True if ROCE clears the relevant benchmark, False if it doesn't,
    None if ROCE is undefined. For companies in the Financials broad_sector,
    uses a sector-relative benchmark (e.g. sector median ROCE) instead of the
    fixed absolute threshold, since balance-sheet structure differs
    fundamentally for banks/NBFCs/insurers.
    """
    if roce_pct is None:
        return None
    if is_financials_sector and sector_relative_benchmark is not None:
        return roce_pct >= sector_relative_benchmark
    return roce_pct >= absolute_threshold


def return_on_assets(net_profit: float, total_assets: float) -> Optional[float]:
    """ROA % = net_profit / total_assets * 100."""
    if total_assets in (0, None) or total_assets == 0:
        return None
    return round((net_profit / total_assets) * 100, 4)


# --------------------------- Day 09: Leverage & Efficiency --------------------

def debt_to_equity(borrowings: float, equity_capital: float, reserves: float) -> Optional[float]:
    """
    D/E = borrowings / (equity_capital + reserves).
    Returns 0 (not None) when borrowings == 0 -- debt-free is a defined value.
    Returns None only when the equity+reserves denominator is non-positive
    AND the company actually carries debt (division is genuinely undefined).
    """
    borrowings = borrowings or 0
    denom = (equity_capital or 0) + (reserves or 0)
    if borrowings == 0:
        return 0.0
    if denom <= 0:
        return None
    return round(borrowings / denom, 4)


def high_leverage_flag(de_ratio: Optional[float], is_financials_sector: bool,
                        threshold: float = 5.0) -> bool:
    """True if D/E > threshold AND the company is NOT in the Financials sector."""
    if de_ratio is None or is_financials_sector:
        return False
    return de_ratio > threshold


def interest_coverage_ratio(operating_profit: float, other_income: float,
                             interest: float) -> Optional[float]:
    """ICR = (operating_profit + other_income) / interest."""
    interest = interest or 0
    if interest == 0:
        return None
    return round(((operating_profit or 0) + (other_income or 0)) / interest, 4)


def icr_label(icr: Optional[float]) -> Optional[str]:
    """Returns 'Debt Free' when ICR is None because interest == 0, else None."""
    return "Debt Free" if icr is None else None


def icr_warning_flag(icr: Optional[float], threshold: float = 1.5) -> bool:
    """True if ICR is defined and below the risk threshold."""
    return icr is not None and icr < threshold


def net_debt(borrowings: float, investments: float) -> float:
    """Net Debt = borrowings - investments (investments used as liquid-asset proxy)."""
    return round((borrowings or 0) - (investments or 0), 4)


def asset_turnover(sales: float, total_assets: float) -> Optional[float]:
    """Asset Turnover = sales / total_assets."""
    if total_assets in (0, None) or total_assets == 0:
        return None
    return round(sales / total_assets, 4)
