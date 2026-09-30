from pathlib import Path
import re
import pandas as pd
from src.common import ROOT, OUT, connect, read_table, company_table, load_financial, col, numeric

PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%", re.I)
METRICS = {
    "compounded_sales_growth":"compounded_sales_growth",
    "compounded_profit_growth":"compounded_profit_growth",
    "stock_price_cagr":"stock_price_cagr",
    "roe":"roe",
}

def _analysis_path():
    for p in [ROOT/'analysis.xlsx', ROOT/'data'/'analysis.xlsx', ROOT/'data'/'raw'/'analysis.xlsx', ROOT/'output'/'analysis.xlsx']:
        if p.exists(): return p
    raise FileNotFoundError('analysis.xlsx not found in project root, data/, data/raw/, or output/.')

def parse_analysis():
    path=_analysis_path()
    sheets=pd.read_excel(path,sheet_name=None)
    rows=[]; failures=[]
    for sheet,d in sheets.items():
        d.columns=[str(c).strip() for c in d.columns]
        idc=col(d,['company_id','id','ticker','symbol'])
        if idc is None: continue
        for metric,needle in METRICS.items():
            mc=col(d,[needle, metric])
            if mc is None: continue
            for _,r in d.iterrows():
                cid=str(r[idc])
                raw='' if pd.isna(r[mc]) else str(r[mc])
                m=PATTERN.search(raw)
                if m:
                    rows.append({'company_id':cid,'metric_type':metric,'period_years':int(m.group(1)),'value_pct':float(m.group(2))})
                elif raw.strip():
                    failures.append({'company_id':cid,'metric_type':metric,'raw_value':raw,'reason':'regex_no_match'})
    parsed=pd.DataFrame(rows,columns=['company_id','metric_type','period_years','value_pct'])
    fails=pd.DataFrame(failures,columns=['company_id','metric_type','raw_value','reason'])
    parsed.to_csv(OUT/'analysis_parsed.csv',index=False); fails.to_csv(OUT/'parse_failures.csv',index=False)
    _cross_validate(parsed)
    return parsed,fails

def _cross_validate(parsed):
    flags=[]
    try:
        with connect() as con:
            fin=load_financial(con); r=fin['ratios']
        if r.empty:return
        idc='_company_id'; yc='_year'
        candidates=[c for c in r.columns if 'cagr' in c.lower()]
        for metric in ['compounded_sales_growth','compounded_profit_growth','stock_price_cagr']:
            target=[c for c in candidates if metric.replace('compounded_','') in c.lower() or ('sales' in c.lower() and metric=='compounded_sales_growth') or ('profit' in c.lower() and metric=='compounded_profit_growth') or ('stock' in c.lower() and metric=='stock_price_cagr')]
            if not target: continue
            rc=target[0]
            rr=r[[idc,rc]].copy(); rr['ratio_value']=pd.to_numeric(rr[rc],errors='coerce'); rr=rr.dropna().groupby(idc)['ratio_value'].last()
            pp=parsed[parsed.metric_type.eq(metric)].groupby('company_id').tail(1)
            for _,x in pp.iterrows():
                rv=rr.get(str(x.company_id)); pv=x.value_pct
                if pd.notna(rv) and abs(rv)>1e-9 and abs((pv-rv)/rv)*100>5:
                    flags.append({'company_id':x.company_id,'metric_type':metric,'parsed_pct':pv,'ratio_engine_pct':rv,'divergence_pct':abs((pv-rv)/rv)*100,'flag':'MANUAL_REVIEW'})
    except Exception as e:
        flags.append({'company_id':'','metric_type':'','parsed_pct':'','ratio_engine_pct':'','divergence_pct':'','flag':f'validation_error:{e}'})
    pd.DataFrame(flags).to_csv(OUT/'cagr_divergence_flags.csv',index=False)

if __name__=='__main__':
    p,f=parse_analysis(); print(f'Parsed {len(p)} rows; failures {len(f)}')
