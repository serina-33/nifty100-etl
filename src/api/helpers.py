"""Shared API helpers."""
from fastapi import HTTPException
import pandas as pd
from src.common import connect, company_table, load_financial, latest_by_company, col, numeric, find_table, tables, read_table

def companies_latest():
    """Return company master joined to latest ratio data."""
    con=connect(); comps=company_table(con); ratios=load_financial(con)['ratios']; con.close(); r=latest_by_company(ratios)
    return comps.merge(r,left_on='company_id',right_on='_company_id',how='left',suffixes=('','_ratio'))

def company_or_404(ticker):
    """Find a company by ticker or raise HTTP 404."""
    d=companies_latest(); x=d[d['ticker'].astype(str).str.upper()==ticker.upper()]
    if x.empty: raise HTTPException(404,detail=f'Ticker {ticker} not found')
    return x.iloc[0]

def financial_history(ticker,kind,from_year=None,to_year=None,year=None):
    """Return filtered financial history for one ticker."""
    con=connect(); c=company_or_404(ticker); d=load_financial(con)[kind]; con.close()
    d=d[d['_company_id'].astype(str)==str(c['company_id'])].copy()
    if from_year: d=d[d['_year']>=int(str(from_year)[:4])]
    if to_year: d=d[d['_year']<=int(str(to_year)[:4])]
    if year: d=d[d['_year']==int(str(year)[:4])]
    return d.drop(columns=[x for x in ['_company_id','_year'] if x in d],errors='ignore')

def records(df):
    """Convert a DataFrame into JSON-safe records."""
    if df is None: return []
    return df.astype(object).where(pd.notna(df),None).to_dict(orient='records')

def ratios_df():
    """Load the ratio table."""
    con=connect(); d=load_financial(con)['ratios']; con.close(); return d
