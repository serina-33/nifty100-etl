from fastapi import APIRouter,HTTPException
from src.api.helpers import company_or_404
from src.common import connect,tables,find_table,read_table,col
from urllib.request import Request,urlopen
router=APIRouter(prefix='/companies',tags=['documents'])

def valid_url(url):
    """Perform a short HEAD/GET validation for a document URL."""
    if not isinstance(url,str) or not url.startswith(('http://','https://')): return False
    try:
        r=urlopen(Request(url,method='HEAD'),timeout=4); return 200<=r.status<400
    except Exception: return False
@router.get('/{ticker}/documents')
def documents(ticker:str):
    """Return annual-report links and URL validity flags."""
    c=company_or_404(ticker); con=connect(); t=find_table(tables(con),['annual_reports','annual_reports_documents','documents','reports']); d=read_table(t,con) if t else None; con.close()
    if d is None or d.empty: return []
    idc=col(d,['company_id','id']); tick=col(d,['ticker','symbol']); x=d[d[idc].astype(str)==str(c['company_id'])] if idc else d[d[tick].astype(str).str.upper()==ticker.upper()]
    uc=col(x,['url','report_url','document_url','link','annual_report_url'])
    rows=[]
    for r in x.to_dict('records'):
        u=r.get(uc) if uc else None; r['is_url_valid']=valid_url(u); rows.append(r)
    return rows
