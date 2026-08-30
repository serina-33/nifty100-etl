"""
tests/kpi/test_cashflow_kpis.py — Sprint 2, Day 11 deliverable
Run with: pytest tests/kpi/test_cashflow_kpis.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "analytics"))
from cashflow_kpis import (  # noqa: E402
    free_cash_flow, cfo_quality_score, capex_intensity,
    fcf_conversion_rate, capital_allocation_pattern,
)


def test_free_cash_flow_positive():
    assert free_cash_flow(1000, -300) == 700

def test_free_cash_flow_negative_allowed():
    assert free_cash_flow(100, -500) == -400

def test_cfo_quality_high_quality_label():
    ratio, label = cfo_quality_score([150, 160, 170], [100, 100, 100])
    assert label == "High Quality"

def test_cfo_quality_accrual_risk_label():
    ratio, label = cfo_quality_score([30, 20, 25], [100, 100, 100])
    assert label == "Accrual Risk"

def test_cfo_quality_no_pat_returns_none():
    ratio, label = cfo_quality_score([100, 100], [0, 0])
    assert ratio is None and label is None

def test_capex_intensity_asset_light():
    value, label = capex_intensity(-20, 1000)
    assert label == "Asset Light"

def test_capex_intensity_capital_intensive():
    value, label = capex_intensity(-150, 1000)
    assert label == "Capital Intensive"

def test_capex_intensity_zero_sales_returns_none():
    value, label = capex_intensity(-50, 0)
    assert value is None and label is None

def test_fcf_conversion_zero_operating_profit_returns_none():
    assert fcf_conversion_rate(500, 0) is None

def test_fcf_conversion_normal_case():
    assert fcf_conversion_rate(400, 500) == 80.0

def test_capital_allocation_reinvestor():
    assert capital_allocation_pattern(100, -50, -20, cfo_pat_ratio=0.9) == "Reinvestor"

def test_capital_allocation_shareholder_returns():
    assert capital_allocation_pattern(100, -50, -20, cfo_pat_ratio=1.5) == "Shareholder Returns"

def test_capital_allocation_distress_signal():
    assert capital_allocation_pattern(-50, 30, 40) == "Distress Signal"

def test_capital_allocation_growth_funded_by_debt():
    assert capital_allocation_pattern(-50, -30, 100) == "Growth Funded by Debt"

def test_capital_allocation_cash_accumulator():
    assert capital_allocation_pattern(100, 50, 20) == "Cash Accumulator"

def test_capital_allocation_pre_revenue():
    assert capital_allocation_pattern(-50, -30, -10) == "Pre-Revenue"

def test_capital_allocation_liquidating_assets():
    assert capital_allocation_pattern(100, 50, -20) == "Liquidating Assets"

def test_capital_allocation_mixed():
    assert capital_allocation_pattern(100, -50, 20) == "Mixed"
