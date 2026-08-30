"""
test_pipeline.py — Day 07 deliverable
Integration-level checks against the built nifty100.db, exercising the
Definition of Done / exit criteria for Sprint 1.
Run with: pytest tests/etl/test_pipeline.py -v
(Requires `python3 src/etl/loader.py` to have been run first.)
"""
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"


@pytest.fixture(scope="module")
def conn():
    if not DB_PATH.exists():
        pytest.skip("nifty100.db not built yet — run `python3 src/etl/loader.py` first")
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA foreign_keys = ON;")
    yield c
    c.close()


def test_companies_count_is_92(conn):
    n = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    assert n == 92


def test_foreign_key_check_zero_violations(conn):
    violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    assert violations == []


def test_all_ten_plus_tables_exist(conn):
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    expected = {"companies", "profitandloss", "balancesheet", "cashflow", "analysis",
                "documents", "prosandcons", "sectors", "stock_prices",
                "financial_ratios", "peer_groups"}
    assert expected.issubset(tables)


def test_profitandloss_has_rows(conn):
    n = conn.execute("SELECT COUNT(*) FROM profitandloss").fetchone()[0]
    assert n > 1000


def test_balancesheet_has_rows(conn):
    n = conn.execute("SELECT COUNT(*) FROM balancesheet").fetchone()[0]
    assert n > 1000


def test_cashflow_has_rows(conn):
    n = conn.execute("SELECT COUNT(*) FROM cashflow").fetchone()[0]
    assert n > 900


def test_stock_prices_row_count(conn):
    n = conn.execute("SELECT COUNT(*) FROM stock_prices").fetchone()[0]
    assert n == 5520


def test_no_duplicate_company_year_in_pl(conn):
    dupes = conn.execute(
        "SELECT company_id, year, COUNT(*) c FROM profitandloss "
        "GROUP BY company_id, year HAVING c > 1").fetchall()
    assert dupes == []


def test_no_null_tickers(conn):
    n = conn.execute("SELECT COUNT(*) FROM companies WHERE ticker IS NULL").fetchone()[0]
    assert n == 0


def test_tickers_are_uppercase(conn):
    rows = conn.execute("SELECT ticker FROM companies").fetchall()
    assert all(t[0] == t[0].upper() for t in rows)
