from pathlib import Path
import re, sqlite3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / 'nifty100.db'
OUT = ROOT / 'output'; REPORTS = ROOT / 'reports'; DOCS = ROOT / 'docs'
for p in (OUT, REPORTS, DOCS): p.mkdir(exist_ok=True)


def norm(s):
    """Normalize a database column or table name."""
    return re.sub(r'[^a-z0-9]+', '_', str(s).strip().lower()).strip('_')


def connect():
    """Open the project SQLite database."""
    if not DB.exists(): raise FileNotFoundError(f'Database not found: {DB}')
    con = sqlite3.connect(DB, check_same_thread=False)
    con.execute('PRAGMA foreign_keys=ON')
    return con


def tables(con):
    """Return all SQLite table names."""
    return pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", con)['name'].tolist()


def read_table(name, con=None):
    """Read a SQLite table into a DataFrame with normalized columns."""
    own = con is None
    con = con or connect()
    try:
        d = pd.read_sql_query(f'SELECT * FROM "{name}"', con)
        d.columns = [norm(c) for c in d.columns]
        return d
    finally:
        if own: con.close()


def find_table(available, candidates):
    """Find a table using exact and fuzzy candidate names."""
    m = {norm(x): x for x in available}
    for c in candidates:
        if norm(c) in m: return m[norm(c)]
    for x in available:
        nx = norm(x)
        if any(norm(c) in nx or nx in norm(c) for c in candidates): return x
    return None


def col(df, candidates, required=False):
    """Find a DataFrame column using exact and fuzzy candidate names."""
    if df is None or df.empty:
        if required: raise KeyError(f'Missing required column; tried {candidates}')
        return None
    m = {norm(c): c for c in df.columns}
    for c in candidates:
        if norm(c) in m: return m[norm(c)]
    for c in candidates:
        nc = norm(c)
        for k, v in m.items():
            if nc == k or nc in k or k in nc: return v
    if required: raise KeyError(f'Missing required column; tried {candidates}; actual={list(df.columns)}')
    return None


def numeric(df, c):
    """Convert a column to numeric values safely."""
    return pd.to_numeric(df[c], errors='coerce') if c and c in df.columns else pd.Series(np.nan, index=df.index)


def years(df):
    """Extract financial years from common year/date columns."""
    c = col(df, ['year','financial_year','fy','period_year'])
    if c:
        return pd.to_numeric(df[c].astype(str).str.extract(r'(20\d{2}|19\d{2})', expand=False), errors='coerce')
    c = col(df, ['date','report_date','period','month'])
    if c:
        return pd.to_datetime(df[c], errors='coerce').dt.year
    return pd.Series(np.nan, index=df.index)


def company_table(con=None):
    """Return a normalized company master DataFrame."""
    own = con is None; con = con or connect()
    try:
        t = find_table(tables(con), ['companies','company_master','dim_company'])
        if not t: raise RuntimeError('companies table not found')
        d = read_table(t, con)
        idc = col(d, ['company_id','id'], True); namec = col(d, ['company_name','name','company'], True)
        tick = col(d, ['ticker','symbol','stock_symbol']); sec = col(d, ['broad_sector','sector','industry'])
        sub = col(d, ['sub_sector','subsector']); mc = col(d, ['market_cap_category','market_cap_class'])
        out = pd.DataFrame({'company_id': d[idc].astype(str), 'company_name': d[namec].astype(str)})
        out['ticker'] = d[tick].astype(str) if tick else out['company_name']
        out['broad_sector'] = d[sec].astype(str) if sec else 'Unknown'
        out['sub_sector'] = d[sub].astype(str) if sub else 'Unknown'
        if mc: out['market_cap_category'] = d[mc].astype(str)
        for c in d.columns:
            if c not in out.columns and c not in {'_company_id'}: out[c] = d[c]
        return out
    finally:
        if own: con.close()


def load_financial(con=None):
    """Load normalized P&L, balance sheet, cash flow and ratio tables."""
    own = con is None; con = con or connect()
    out = {}
    try:
        ts = tables(con)
        for key, cands in {'ratios':['financial_ratios','financial_ratio','ratios'], 'pl':['profitandloss','profit_and_loss','profit_loss','pnl'], 'bs':['balancesheet','balance_sheet','balance'], 'cf':['cashflow','cash_flow','cash_flows']}.items():
            t = find_table(ts, cands); d = read_table(t, con) if t else pd.DataFrame()
            if not d.empty:
                idc = col(d, ['company_id','id']); d['_company_id'] = d[idc].astype(str) if idc else ''
                d['_year'] = years(d)
            out[key] = d
        return out
    finally:
        if own: con.close()


def latest_by_company(df):
    """Return the latest available row for each company."""
    if df.empty: return df.copy()
    if '_year' not in df: df['_year'] = years(df)
    return df.sort_values('_year').groupby('_company_id', as_index=False).tail(1).copy()


def resolve_metric(df, aliases):
    """Resolve a metric column from aliases."""
    return col(df, aliases)


def value(row, aliases, default=np.nan):
    """Read a numeric value from a row using aliases."""
    for a in aliases:
        if a in row.index:
            x = pd.to_numeric(pd.Series([row[a]]), errors='coerce').iloc[0]
            if pd.notna(x): return float(x)
    return default


def cagr(start, end, periods):
    """Calculate CAGR percentage; return NaN when a standard CAGR is not valid."""
    try:
        if periods <= 0 or start <= 0 or end < 0:
            return np.nan
        return ((end / start) ** (1 / periods) - 1) * 100
    except Exception:
        return np.nan


def streak(values, predicate, n):
    """Return True when the final n values satisfy predicate."""
    vals = list(values)
    if len(vals) < n:
        return False
    return all(predicate(x) for x in vals[-n:])
