from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / 'nifty100.db'

def _connect():
    return sqlite3.connect(DB_PATH)

def _read(sql, params=()):
    with _connect() as con:
        return pd.read_sql_query(sql, con, params=params)

@st.cache_data(ttl=600)
def get_companies():
    return _read('SELECT * FROM companies ORDER BY company_name')

@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    if year is None:
        return _read('''SELECT c.*, r.* FROM companies c JOIN financial_ratios r ON c.company_id=r.company_id WHERE c.ticker=? ORDER BY r.year''', (ticker,))
    return _read('''SELECT c.*, r.* FROM companies c JOIN financial_ratios r ON c.company_id=r.company_id WHERE c.ticker=? AND r.year=? ORDER BY r.year''', (ticker, year))

@st.cache_data(ttl=600)
def get_pl(ticker):
    return _read('''SELECT c.ticker,c.company_name,p.* FROM companies c JOIN profitandloss p ON c.company_id=p.company_id WHERE c.ticker=? ORDER BY p.year''', (ticker,))

@st.cache_data(ttl=600)
def get_bs(ticker):
    return _read('''SELECT c.ticker,c.company_name,b.* FROM companies c JOIN balancesheet b ON c.company_id=b.company_id WHERE c.ticker=? ORDER BY b.year''', (ticker,))

@st.cache_data(ttl=600)
def get_cf(ticker):
    return _read('''SELECT c.ticker,c.company_name,f.* FROM companies c JOIN cashflow f ON c.company_id=f.company_id WHERE c.ticker=? ORDER BY f.year''', (ticker,))

@st.cache_data(ttl=600)
def get_sectors():
    return _read('''SELECT sector, COUNT(*) AS company_count FROM companies GROUP BY sector ORDER BY company_count DESC, sector''')

@st.cache_data(ttl=600)
def get_peers(group_name):
    c = get_companies()
    if c.empty: return c
    if 'peer_group' in c.columns:
        return c[c.peer_group.eq(group_name)].copy()
    return c[c.sector.eq(group_name)].copy()

@st.cache_data(ttl=600)
def get_valuation(ticker):
    p = ROOT / 'output' / 'valuation_summary.xlsx'
    if not p.exists(): return pd.DataFrame()
    d = pd.read_excel(p)
    return d[d.get('ticker', pd.Series(dtype=str)).eq(ticker)].copy() if 'ticker' in d.columns else d

@st.cache_data(ttl=600)
def get_latest_snapshot(year=None):
    with _connect() as con:
        try:
            from src.screener.engine import latest_complete_snapshot
            d = latest_complete_snapshot(con)
        except Exception:
            d = pd.read_sql_query('''SELECT c.*, r.* FROM companies c LEFT JOIN financial_ratios r ON c.company_id=r.company_id''', con)
    if d.empty: return d
    if year is not None and 'year' in d.columns:
        y = pd.to_numeric(d.year, errors='coerce')
        exact = d[y.eq(year)]
        if not exact.empty: d = exact
    return d

@st.cache_data(ttl=600)
def get_reports(ticker):
    try:
        return _read('''SELECT c.ticker,d.* FROM companies c JOIN documents d ON c.company_id=d.company_id WHERE c.ticker=? ORDER BY d.filed_date DESC''', (ticker,))
    except Exception:
        return pd.DataFrame()
