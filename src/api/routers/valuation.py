from fastapi import APIRouter, HTTPException
from src.api.helpers import financial_history, company_or_404, records
from src.common import col
import pandas as pd
router=APIRouter(tags=['valuation'])
@router.get('/companies/{ticker}/peers/compare')
def peer_compare(ticker:str):
    """Return eight-axis radar data for a company, peer average and benchmark."""
    c=company_or_404(ticker)
    from src.api.routers.peers import peer_table
    d=peer_table()
    if d is None or d.empty: return {'ticker':ticker.upper(),'axes':[],'peer_group_average':{},'benchmark_company':{}}
    tc=col(d,['ticker','symbol','company_ticker']); gc=col(d,['group_name','peer_group','group'])
    x=d[d[tc].astype(str).str.upper()==ticker.upper()] if tc else d.iloc[0:0]
    if x.empty: return {'ticker':ticker.upper(),'axes':[],'peer_group_average':{},'benchmark_company':{}}
    group=x.iloc[0][gc] if gc else None; g=d[d[gc]==group] if gc else d
    exclude={'company_id','ticker','company_name','group_name','peer_group','group','year'}
    nums=[]
    for cc in d.columns:
        if cc in exclude: continue
        s=pd.to_numeric(g[cc],errors='coerce')
        if s.notna().mean()>.5: nums.append(cc)
    nums=nums[:8]
    company_vals={k:pd.to_numeric(x.iloc[0][k],errors='coerce') for k in nums}
    avg={k:pd.to_numeric(g[k],errors='coerce').mean() for k in nums}
    benchmark={k:pd.to_numeric(g[k],errors='coerce').max() for k in nums}
    return {'ticker':ticker.upper(),'peer_group':group,'axes':nums,'company':company_vals,'peer_group_average':avg,'benchmark_company':benchmark}
@router.get('/market-cap/{ticker}')
def market_cap(ticker:str):
    """Return 2019-2024 valuation multiple history."""
    company_or_404(ticker); d=financial_history(ticker,'ratios')
    aliases={'pe':['pe','pe_ratio','price_to_earnings'],'pb':['pb','pb_ratio','price_to_book'],'ev_ebitda':['ev_ebitda','ev_to_ebitda'],'dividend_yield':['dividend_yield','dividend_yield_pct']}
    yearcol=col(d,['year','financial_year','fy','period_year']); x=pd.DataFrame()
    x['year']=d[yearcol] if yearcol else pd.NA
    for out,a in aliases.items():
        cc=col(d,a); x[out]=d[cc] if cc else pd.NA
    y=pd.to_numeric(x['year'],errors='coerce'); x=x[(y>=2019)&(y<=2024)]
    return {'ticker':ticker.upper(),'history':records(x)}
