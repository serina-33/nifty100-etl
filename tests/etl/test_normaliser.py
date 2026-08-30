"""
test_normaliser.py — Day 02 deliverable
20 unit tests for normalize_year() + 15 unit tests for normalize_ticker()
= 35 unit tests total (meets the 35+ requirement).
Run with: pytest tests/etl/test_normaliser.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "etl"))
from normaliser import normalize_year, normalize_ticker  # noqa: E402


# ============================= normalize_year (20 tests) =====================

def test_year_plain_int():
    assert normalize_year(2023) == 2023

def test_year_plain_string():
    assert normalize_year("2023") == 2023

def test_year_with_whitespace():
    assert normalize_year(" 2023 ") == 2023

def test_year_fy_prefix():
    assert normalize_year("FY2023") == 2023

def test_year_fy_prefix_lowercase():
    assert normalize_year("fy2023") == 2023

def test_year_fy_range():
    assert normalize_year("FY2023-24") == 2023

def test_year_range_no_prefix():
    assert normalize_year("2023-24") == 2023

def test_year_fy_space():
    assert normalize_year("FY 2023") == 2023

def test_year_float_like():
    assert normalize_year("2023.0") == 2023

def test_year_two_digit_recent():
    assert normalize_year("FY23") == 2023

def test_year_two_digit_older_1900s():
    assert normalize_year("FY95") == 1995

def test_year_none_returns_none():
    assert normalize_year(None) is None

def test_year_empty_string_returns_none():
    assert normalize_year("") is None

def test_year_na_string_returns_none():
    assert normalize_year("N/A") is None

def test_year_null_string_returns_none():
    assert normalize_year("NULL") is None

def test_year_nan_float_returns_none():
    assert normalize_year(float("nan")) is None

def test_year_garbage_string_returns_none():
    assert normalize_year("not a year") is None

def test_year_out_of_range_low():
    assert normalize_year("1850") is None

def test_year_out_of_range_high():
    assert normalize_year("2200") is None

def test_year_int_type_returned():
    assert isinstance(normalize_year("FY2023"), int)


# ============================= normalize_ticker (15 tests) ===================

def test_ticker_plain():
    assert normalize_ticker("INFY") == "INFY"

def test_ticker_lowercase():
    assert normalize_ticker("infy") == "INFY"

def test_ticker_ns_suffix():
    assert normalize_ticker("INFY.NS") == "INFY"

def test_ticker_ns_suffix_lowercase():
    assert normalize_ticker("infy.ns") == "INFY"

def test_ticker_bo_suffix():
    assert normalize_ticker("RELIANCE.BO") == "RELIANCE"

def test_ticker_eq_suffix():
    assert normalize_ticker("TCS-EQ") == "TCS"

def test_ticker_be_suffix():
    assert normalize_ticker("YESBANK-BE") == "YESBANK"

def test_ticker_bz_suffix():
    assert normalize_ticker("SMALLCO-BZ") == "SMALLCO"

def test_ticker_whitespace_padding():
    assert normalize_ticker("  HDFCBANK  ") == "HDFCBANK"

def test_ticker_internal_whitespace_removed():
    assert normalize_ticker("HDFC BANK") == "HDFCBANK"

def test_ticker_mixed_case_with_suffix_and_space():
    assert normalize_ticker(" infy.ns ") == "INFY"

def test_ticker_none_returns_none():
    assert normalize_ticker(None) is None

def test_ticker_empty_string_returns_none():
    assert normalize_ticker("") is None

def test_ticker_whitespace_only_returns_none():
    assert normalize_ticker("   ") is None

def test_ticker_str_type_returned():
    assert isinstance(normalize_ticker("infy.ns"), str)
