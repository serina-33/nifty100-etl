from fastapi import APIRouter, HTTPException
from src.api.helpers import companies_latest
from src.common import col,numeric
router=APIRouter(prefix='/sectors',tags=['sectors'])
@router.get('')
def sectors():
    """Return sector counts and median valuation/quality metrics."""
    d=companies_latest(); rows=[]
    for s,g in d.groupby('broad_sector',dropna=False):
        rows.append({'sector':s,'company_count':len(g),'median_roe':numeric(g,col(g,['return_on_equity_pct','roe_percentage','roe_pct','roe'])).median(),'median_pe':numeric(g,col(g,['pe','pe_ratio'])).median(),'median_de':numeric(g,col(g,['debt_to_equity','de_ratio'])).median()})
    return rows
@router.get('/{sector}/companies')
def sector_companies(sector:str):
    """Return companies belonging to one sector."""
    d=companies_latest(); x=d[d['broad_sector'].astype(str).str.lower()==sector.lower()]
    if x.empty: raise HTTPException(404,detail='Unknown sector')
    return x.astype(object).where(x.notna(),None).to_dict('records')
