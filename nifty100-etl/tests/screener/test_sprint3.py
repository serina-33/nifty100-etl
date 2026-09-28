import pandas as pd
import numpy as np

from src.screener.engine import (
    apply_filters,
    winsor_scale,
    compute_composite_score,
)


def sample():
    return pd.DataFrame({
        "roe": [20, 10, 25],
        "roce": [18, 12, 30],
        "npm": [12, 5, 15],
        "opm": [20, 10, 25],
        "de": [0.5, 2.0, 0.2],
        "icr": [5, 2, 10],
        "fcf": [100, -10, 200],
        "revenue_cagr_5yr": [12, 8, 20],
        "pat_cagr_5yr": [22, 10, 25],
        "eps_cagr_5yr": [15, 5, 20],
        "asset_turnover": [1.0, 0.3, 1.2],
        "pe": [15, 25, 12],
        "pb": [2, 4, 1.5],
        "dividend_yield": [2, 0.5, 3],
        "market_cap_cr": [10000, 3000, 20000],
        "net_profit": [1000, 200, 1500],
        "sales": [8000, 4000, 12000],
        "payout": [50, 90, 40],
        "fcf_positive": [True, False, True],
        "de_declining_yoy": [True, False, True],
        "broad_sector": ["Industrials"] * 3,
    })


def test_01_min_filter():
    result = apply_filters(
        sample(),
        {"roe_min": 15}
    )

    assert len(result) == 2


def test_02_max_filter():
    result = apply_filters(
        sample(),
        {"de_max": 1}
    )

    assert len(result) == 2


def test_03_fcf_positive():
    result = apply_filters(
        sample(),
        {"fcf_latest_positive": True}
    )

    assert len(result) == 2


def test_04_payout():
    result = apply_filters(
        sample(),
        {"dividend_payout_max": 80}
    )

    assert len(result) == 2


def test_05_multiple():
    result = apply_filters(
        sample(),
        {
            "roe_min": 15,
            "de_max": 1,
        }
    )

    assert len(result) == 2


def test_06_winsor():
    x = winsor_scale(
        pd.Series([1, 2, 3, 100])
    )

    assert x.min() >= 0
    assert x.max() <= 100


def test_07_inverse():
    x = winsor_scale(
        pd.Series([1, 2, 3]),
        higher_is_better=False,
    )

    assert x.iloc[0] > x.iloc[-1]


def test_08_composite():
    d = sample()

    result = compute_composite_score(d)

    assert result["composite_quality_score"].between(
        0, 100
    ).all()


def test_09_columns():
    result = compute_composite_score(sample())

    assert "profitability_score" in result.columns
    assert "growth_score" in result.columns


def test_10_sector_score():
    result = compute_composite_score(sample())

    assert "sector_relative_composite_score" in result.columns


def test_11_nan_safe():
    d = sample()

    d.loc[0, "roe"] = np.nan

    result = compute_composite_score(d)

    assert len(result) == 3


def test_12_sort():
    result = compute_composite_score(sample())

    assert result["composite_quality_score"].is_monotonic_decreasing


def test_13_debt_free():
    d = sample()

    d.loc[0, "de"] = 0

    result = apply_filters(
        d,
        {"de_max": 0}
    )

    assert len(result) >= 1


def test_14_turnaround_flags():
    result = apply_filters(
        sample(),
        {
            "revenue_cagr_5yr_min": 10,
            "fcf_latest_positive": True,
            "de_declining_yoy": True,
        }
    )

    assert len(result) == 2
    