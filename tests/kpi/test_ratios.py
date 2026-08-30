"""
tests/kpi/test_ratios.py — Sprint 2, Day 08-09 deliverable
Run with: pytest tests/kpi/test_ratios.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "analytics"))
from ratios import (  # noqa: E402
    net_profit_margin, operating_profit_margin, opm_cross_check,
    return_on_equity, return_on_capital_employed, roce_benchmark_check,
    return_on_assets, debt_to_equity, high_leverage_flag,
    interest_coverage_ratio, icr_label, icr_warning_flag, net_debt, asset_turnover,
)


# ---------------------------- Day 08: Profitability (10 tests) ----------------

def test_net_profit_margin_normal_case():
    assert net_profit_margin(200, 1000) == 20.0

def test_net_profit_margin_zero_sales_returns_none():
    assert net_profit_margin(200, 0) is None

def test_operating_profit_margin_normal_case():
    assert operating_profit_margin(300, 1000) == 30.0

def test_operating_profit_margin_zero_sales_returns_none():
    assert operating_profit_margin(300, 0) is None

def test_opm_cross_check_within_tolerance():
    result = opm_cross_check(30.2, 30.0, tolerance_pp=1.0)
    assert result["mismatch"] is False

def test_opm_cross_check_mismatch_flagged():
    result = opm_cross_check(35.0, 30.0, tolerance_pp=1.0)
    assert result["mismatch"] is True

def test_roe_normal_case():
    assert return_on_equity(100, 200, 300) == 20.0

def test_roe_negative_equity_returns_none():
    assert return_on_equity(100, -500, 100) is None

def test_roce_normal_case():
    assert return_on_capital_employed(150, 200, 300, 500) == 15.0

def test_roa_zero_assets_returns_none():
    assert return_on_assets(100, 0) is None


# ---------------------------- Day 09: Leverage & Efficiency (10 tests) --------

def test_de_debt_free_returns_zero_not_none():
    assert debt_to_equity(0, 200, 300) == 0.0

def test_de_normal_case():
    assert debt_to_equity(250, 200, 300) == 0.5

def test_de_negative_equity_with_debt_returns_none():
    assert debt_to_equity(100, -500, 100) is None

def test_high_leverage_flag_true_for_non_financials():
    assert high_leverage_flag(6.0, is_financials_sector=False) is True

def test_high_leverage_flag_suppressed_for_financials():
    assert high_leverage_flag(6.0, is_financials_sector=True) is False

def test_icr_interest_zero_returns_none():
    assert interest_coverage_ratio(100, 10, 0) is None

def test_icr_label_debt_free():
    icr = interest_coverage_ratio(100, 10, 0)
    assert icr_label(icr) == "Debt Free"

def test_icr_label_none_when_icr_defined():
    icr = interest_coverage_ratio(100, 10, 50)
    assert icr_label(icr) is None

def test_icr_warning_flag_true_below_threshold():
    assert icr_warning_flag(1.0) is True

def test_icr_warning_flag_false_above_threshold():
    assert icr_warning_flag(2.0) is False

def test_net_debt_calculation():
    assert net_debt(1000, 300) == 700

def test_asset_turnover_zero_assets_returns_none():
    assert asset_turnover(500, 0) is None

def test_asset_turnover_normal_case():
    assert asset_turnover(500, 1000) == 0.5

def test_roce_benchmark_absolute_threshold():
    assert roce_benchmark_check(20.0, is_financials_sector=False) is True
    assert roce_benchmark_check(10.0, is_financials_sector=False) is False

def test_roce_benchmark_sector_relative_for_financials():
    assert roce_benchmark_check(12.0, is_financials_sector=True, sector_relative_benchmark=10.0) is True
    assert roce_benchmark_check(8.0, is_financials_sector=True, sector_relative_benchmark=10.0) is False
