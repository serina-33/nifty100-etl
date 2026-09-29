from typing import Optional
from fastapi import APIRouter, HTTPException
import pandas as pd, numpy as np
from src.api.helpers import companies_latest
from src.common import col,numeric
router=APIRouter(prefix='/screener',tags=['screener'])

def _num(d,aliases):
    c=col(d,aliases); return numeric(d,c) if c else pd.Series(np.nan,index=d.index)

@router.get('')
def screener(min_roe:Optional[float]=None,max_de:Optional[float]=None,min_fcf:Optional[float]=None,sector:Optional[str]=None,min_rev_cagr_5yr:Optional[float]=None,min_pat_cagr_5yr:Optional[float]=None,max_pe:Optional[float]=None):
    """Filter and rank companies using core screener metrics."""
    vals=[x for x in [min_roe,max_de,min_fcf,min_rev_cagr_5yr,min_pat_cagr_5yr,max_pe] if x is not None]
    if any(not np.isfinite(x) for x in vals): raise HTTPException(400,'All numeric parameters must be finite')
    d=companies_latest().copy()
    roe=_num(d,['return_on_equity_pct','roe_percentage','roe_pct','roe']); de=_num(d,['debt_to_equity','de_ratio','debt_equity']); fcf=_num(d,['free_cash_flow','fcf','free_cash_flow_latest','fcf_latest']); rev=_num(d,['revenue_cagr_5yr','sales_cagr_5yr','revenue_cagr']); pat=_num(d,['pat_cagr_5yr','profit_cagr_5yr','net_profit_cagr_5yr']); pe=_num(d,['pe','pe_ratio','price_to_earnings'])
    if min_roe is not None:d=d[roe>=min_roe]
    if max_de is not None:d=d[de<=max_de]
    if min_fcf is not None:d=d[fcf>=min_fcf]
    if sector:d=d[d['broad_sector'].astype(str).str.contains(sector,case=False,na=False)]
    if min_rev_cagr_5yr is not None:d=d[rev>=min_rev_cagr_5yr]
    if min_pat_cagr_5yr is not None:d=d[pat>=min_pat_cagr_5yr]
    if max_pe is not None:d=d[pe<=max_pe]
    d=d.copy(); d['roe_pct']=roe.loc[d.index]; d['debt_to_equity']=de.loc[d.index]; d['fcf']=fcf.loc[d.index]; d['revenue_cagr_5yr']=rev.loc[d.index]; d['pat_cagr_5yr']=pat.loc[d.index]; d['pe']=pe.loc[d.index]
    d=d.sort_values(['roe_pct','revenue_cagr_5yr'],ascending=False,na_position='last')
    return d.astype(object).where(pd.notna(d),None).to_dict('records')
