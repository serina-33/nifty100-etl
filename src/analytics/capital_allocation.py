import pandas as pd, numpy as np
from src.common import OUT, connect, company_table, load_financial, col
from src.analytics.cashflow_kpis import _one

def build():
    with connect() as con: companies=company_table(con); fin=load_financial(con)
    cf=fin['cf']; bs=fin['bs']; rows=[]
    for _,co in companies.iterrows():
        cid=co.company_id; cfo=_one(cf,cid,['cash_from_operations','cfo','net_cash_from_operating_activities']); cfi=_one(cf,cid,['cash_from_investing','cfi','net_cash_from_investing_activities']); cff=_one(cf,cid,['cash_from_financing','cff','net_cash_from_financing_activities']); debt=_one(bs,cid,['total_debt','borrowings','debt','total_borrowings'])
        f=pd.DataFrame({'year':cfo.year,'cfo':cfo.v}).merge(pd.DataFrame({'year':cfi.year,'cfi':cfi.v}),on='year',how='outer').merge(pd.DataFrame({'year':cff.year,'cff':cff.v}),on='year',how='outer').sort_values('year').fillna(0)
        if f.empty: continue
        prev=None
        for _,r in f.iterrows():
            if r.cfo>=0 and r.cfi<0 and r.cff<0: label='Self-funded Growth'
            elif r.cfo>=0 and r.cfi<0 and r.cff>=0: label='External-funded Growth'
            elif r.cfo>=0 and r.cfi>=0 and r.cff<0: label='Harvest / Distribution'
            elif r.cfo<0 and r.cfi<0 and r.cff>=0: label='Funding-led Investment'
            elif r.cfo<0 and r.cfi>=0 and r.cff>=0: label='Restructuring / Liquidity Raise'
            elif r.cfo<0 and r.cfi>=0 and r.cff<0: label='Asset Monetisation'
            elif r.cfo>=0 and r.cfi>=0 and r.cff>=0: label='Cash Accumulation'
            else: label='Cash Burn'
            rows.append({'company_id':cid,'year':int(r.year),'capital_allocation_label':label})
    out=pd.DataFrame(rows); out.to_csv(OUT/'capital_allocation.csv',index=False)
    # 8-pattern latest-year distribution and YoY changes.
    latest=out.sort_values('year').groupby('company_id').tail(1); latest[['capital_allocation_label']].value_counts().rename('company_count').reset_index().to_csv(OUT/'capital_allocation_distribution.csv',index=False)
    x=out.sort_values(['company_id','year']).copy(); x['previous_pattern']=x.groupby('company_id').capital_allocation_label.shift(1); ch=x[x.previous_pattern.notna() & x.capital_allocation_label.ne(x.previous_pattern)][['company_id','year','previous_pattern','capital_allocation_label']]; ch.to_csv(OUT/'pattern_changes.csv',index=False)
    return out

if __name__=='__main__': print(f'Wrote {len(build())} company-year capital allocation rows')
