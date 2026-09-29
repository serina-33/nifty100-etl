from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from src.api.helpers import *
from src.common import OUT, REPORTS
router=APIRouter(prefix='/companies',tags=['companies'])

def _pick(r):
    return {'id':r.get('company_id'),'company_id':r.get('company_id'),'company_name':r.get('company_name'),'ticker':r.get('ticker'),'broad_sector':r.get('broad_sector'),'sub_sector':r.get('sub_sector'),'roe_pct':r.get('return_on_equity_pct',r.get('roe_percentage',r.get('roe_pct'))),'roce_pct':r.get('roce_percentage',r.get('roce_pct'))}

@router.get('')
def list_companies(sector:Optional[str]=None,market_cap_category:Optional[str]=None,search:Optional[str]=None):
    """List all companies with optional filters."""
    d=companies_latest()
    if sector: d=d[d['broad_sector'].astype(str).str.contains(sector,case=False,na=False)]
    if market_cap_category and 'market_cap_category' in d: d=d[d['market_cap_category'].astype(str).str.lower()==market_cap_category.lower()]
    if search: d=d[d['company_name'].astype(str).str.contains(search,case=False,na=False)|d['ticker'].astype(str).str.contains(search,case=False,na=False)]
    return [_pick(r) for r in d.to_dict('records')]

@router.get('/{ticker}')
def company_profile(ticker:str):
    """Return full company profile and latest KPI data."""
    r=company_or_404(ticker); return records(r.to_frame().T)[0]

@router.get('/{ticker}/pl')
def company_pl(ticker:str,from_year:Optional[str]=None,to_year:Optional[str]=None):
    """Return P&L history."""
    return {'ticker':ticker.upper(),'history':records(financial_history(ticker,'pl',from_year,to_year))}
@router.get('/{ticker}/bs')
def company_bs(ticker:str,from_year:Optional[str]=None,to_year:Optional[str]=None):
    """Return balance sheet history."""
    return {'ticker':ticker.upper(),'history':records(financial_history(ticker,'bs',from_year,to_year))}
@router.get('/{ticker}/cashflow')
def company_cashflow(ticker:str,from_year:Optional[str]=None,to_year:Optional[str]=None):
    """Return cash flow history."""
    return {'ticker':ticker.upper(),'history':records(financial_history(ticker,'cf',from_year,to_year))}
@router.get('/{ticker}/ratios')
def company_ratios(ticker:str,year:Optional[str]=None):
    """Return computed KPI history or one year."""
    return {'ticker':ticker.upper(),'history':records(financial_history(ticker,'ratios',year=year))}
@router.get('/{ticker}/tearsheet')
def company_tearsheet(ticker:str):
    """Download the pre-generated company tearsheet PDF."""
    for p in [REPORTS/'tearsheets'/f'{ticker.upper()}_tearsheet.pdf',REPORTS/'tearsheets'/f'{ticker}_tearsheet.pdf']:
        if p.exists(): return FileResponse(p,media_type='application/pdf',filename=p.name)
    from fastapi import HTTPException; raise HTTPException(404,detail='Tearsheet PDF not found; run Sprint 5 report generation first')
