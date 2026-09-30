import pandas as pd, numpy as np
from src.common import OUT, connect, company_table, load_financial, col, numeric, cagr

PROS={
'P01':('ROE >20% sustained 3+ years','Consistently high return on equity above 20% demonstrates exceptional capital efficiency'),
'P02':('FCF positive 5+ consecutive years','Strong free cash flow generation over 5 years signals healthy business fundamentals'),
'P03':('D/E =0 latest','Debt-free balance sheet provides financial flexibility and eliminates interest burden'),
'P04':('Revenue CAGR >15% 5y','Revenue growing at above 15% CAGR over 5 years reflects strong business momentum'),
'P05':('OPM >25% latest','Operating profit margin above 25% indicates strong pricing power and cost discipline'),
'P06':('PAT CAGR >20% 5y','Net profit compounding at above 20% over 5 years creates significant shareholder value'),
'P07':('ICR >10 or Debt Free','Very high interest coverage ratio reflects negligible financial stress from debt servicing'),
'P08':('Dividend Yield >2% with FCF positive','Consistent dividend yield above 2% backed by positive free cash flow'),
'P09':('EPS CAGR >15% 5y','Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding'),
'P10':('ROE improving 3 consecutive years','Return on equity improving for 3 consecutive years shows strengthening business quality'),
'P11':('Revenue CAGR < PAT CAGR','Revenue growing slower than profits shows improving operating leverage and scale benefits'),
'P12':('Assets growing with declining debt','Growing asset base funded by internal accruals reflects self-sustaining growth'),}
CONS={
'C01':('D/E >2 non-financial','High leverage above 2x can increase financial risk and reduce balance-sheet flexibility'),
'C02':('FCF negative 3 consecutive years','Negative free cash flow for 3 consecutive years indicates pressure on internally generated cash'),
'C03':('OPM declining 3 consecutive years','Declining operating margin for 3 consecutive years signals weakening operating efficiency'),
'C04':('Net profit negative latest','A negative latest net profit indicates current profitability pressure'),
'C05':('Revenue declining 2+ years','Declining revenue over 2 or more years signals weakening business demand or scale'),
'C06':('ICR <1.5','Low interest coverage below 1.5x indicates elevated debt-servicing risk'),
'C07':('Dividend payout >100%','Dividend payout above 100% can indicate distributions exceeding current earnings'),
'C08':('D/E rising 3 consecutive years','Rising debt-to-equity for 3 consecutive years indicates increasing leverage'),
'C09':('EPS declining 3 consecutive years','Declining EPS for 3 consecutive years indicates weakening per-share earnings'),
'C10':('ROCE <10%','ROCE below 10% indicates relatively weak returns on invested capital'),
'C11':('Net Debt >3x EBITDA','Net debt above 3x EBITDA indicates elevated leverage relative to operating earnings'),
'C12':('Revenue CAGR <5% 5y','Revenue CAGR below 5% over 5 years indicates slow business growth'),}

def _metric(df,names):
    c=col(df,names); return numeric(df,c) if c else pd.Series(np.nan,index=df.index)

def _series(fin,key,cands,cid,year):
    d=fin[key]
    if d.empty:return pd.DataFrame(columns=['year','v'])
    s=d[d['_company_id'].eq(str(cid))].copy().sort_values('_year')
    c=col(s,cands)
    if c is None:return pd.DataFrame(columns=['year','v'])
    return pd.DataFrame({'year':pd.to_numeric(s['_year'],errors='coerce'),'v':pd.to_numeric(s[c],errors='coerce')}).dropna()

def build():
    with connect() as con:
        companies=company_table(con); fin=load_financial(con)
    r,pl,bs,cf=fin['ratios'],fin['pl'],fin['bs'],fin['cf']
    rows=[]
    for _,co in companies.iterrows():
        cid=co.company_id
        rr=r[r['_company_id'].eq(cid)].sort_values('_year') if not r.empty else pd.DataFrame()
        pp=pl[pl['_company_id'].eq(cid)].sort_values('_year') if not pl.empty else pd.DataFrame()
        bb=bs[bs['_company_id'].eq(cid)].sort_values('_year') if not bs.empty else pd.DataFrame()
        cc=cf[cf['_company_id'].eq(cid)].sort_values('_year') if not cf.empty else pd.DataFrame()
        roe=_series(fin,'ratios',['roe','return_on_equity'],cid,0); opm=_series(fin,'ratios',['opm','operating_profit_margin'],cid,0); de=_series(fin,'ratios',['de_ratio','debt_to_equity','de'],cid,0); icr=_series(fin,'ratios',['interest_coverage_ratio','icr'],cid,0); roce=_series(fin,'ratios',['roce','return_on_capital_employed'],cid,0); dy=_series(fin,'ratios',['dividend_yield'],cid,0); payout=_series(fin,'ratios',['dividend_payout','payout_ratio'],cid,0); eps=_series(fin,'ratios',['eps'],cid,0)
        revenue=_series(fin,'pl',['revenue','sales','total_revenue'],cid,0); pat=_series(fin,'pl',['net_profit','profit_after_tax','pat','net_profit_after_tax'],cid,0); assets=_series(fin,'bs',['total_assets','assets'],cid,0); debt=_series(fin,'bs',['total_debt','borrowings','debt'],cid,0); ebitda=_series(fin,'pl',['ebitda','operating_ebitda'],cid,0); cfo=_series(fin,'cf',['cash_from_operations','cfo','net_cash_from_operating_activities'],cid,0); cfi=_series(fin,'cf',['cash_from_investing','cfi','net_cash_from_investing_activities'],cid,0); cff=_series(fin,'cf',['cash_from_financing','cff','net_cash_from_financing_activities'],cid,0)
        all_years=sorted(set(sum([x.year.dropna().astype(int).tolist() for x in [roe,opm,de,icr,roce,dy,payout,eps,revenue,pat,assets,debt,ebitda,cfo,cfi,cff] if not x.empty],[])))
        latest=max(all_years) if all_years else None
        def last(s): return s[s.year.eq(latest)].v.iloc[-1] if latest is not None and not s[s.year.eq(latest)].empty else np.nan
        def cagr5(s):
            if len(s)<2:return np.nan
            q=s.tail(6)
            return cagr(q.v.iloc[0],q.v.iloc[-1],int(q.year.iloc[-1]-q.year.iloc[0]))
        fcf=pd.DataFrame({'year':cfo.year,'v':cfo.v}).merge(pd.DataFrame({'year':cfi.year,'cfi':cfi.v}),on='year',how='outer'); fcf['v']=fcf.v.fillna(0)+fcf.cfi.fillna(0); fcf=fcf.sort_values('year')
        def score(strength): return float(min(99,max(61,strength)))
        # Evidence-based rules. P11 follows the supplied text: Revenue CAGR < PAT CAGR.
        checks=[
            ('P01', not roe.empty and (roe.tail(3).v>20).all(), 70+min(29,max(0,(roe.tail(3).v.mean()-20)*2)) if not roe.empty else 0),
            ('P02', len(fcf)>=5 and (fcf.tail(5).v>0).all(), 75),
            ('P03', pd.notna(last(de)) and abs(last(de))<1e-9, 90),
            ('P04', pd.notna(cagr5(revenue)) and cagr5(revenue)>15, 75+min(24,cagr5(revenue)-15) if pd.notna(cagr5(revenue)) else 0),
            ('P05', pd.notna(last(opm)) and last(opm)>25, 75+min(24,last(opm)-25) if pd.notna(last(opm)) else 0),
            ('P06', pd.notna(cagr5(pat)) and cagr5(pat)>20, 75+min(24,cagr5(pat)-20) if pd.notna(cagr5(pat)) else 0),
            ('P07', (pd.notna(last(icr)) and last(icr)>10) or (pd.notna(last(de)) and abs(last(de))<1e-9), 88),
            ('P08', pd.notna(last(dy)) and last(dy)>2 and (not fcf.empty and fcf.tail(1).v.iloc[0]>0), 80),
            ('P09', pd.notna(cagr5(eps)) and cagr5(eps)>15, 75+min(24,cagr5(eps)-15) if pd.notna(cagr5(eps)) else 0),
            ('P10', len(roe)>=3 and all(roe.tail(3).v.iloc[i]<roe.tail(3).v.iloc[i+1] for i in range(2)), 80),
            ('P11', pd.notna(cagr5(revenue)) and pd.notna(cagr5(pat)) and cagr5(revenue)<cagr5(pat), 80),
            ('P12', len(assets)>=2 and len(debt)>=2 and assets.v.iloc[-1]>assets.v.iloc[-2] and debt.v.iloc[-1]<debt.v.iloc[-2], 78),]
        for rid,ok,conf in checks:
            if ok and conf>60: rows.append({'company_id':cid,'type':'pro','rule_id':rid,'text':PROS[rid][1],'confidence_pct':round(min(100,conf),1)})
        cchecks=[
            ('C01', co.sector.lower() not in {'banking','nbfc','financial services','insurance','finance'} and pd.notna(last(de)) and last(de)>2, 85),
            ('C02', len(fcf)>=3 and (fcf.tail(3).v<0).all(), 85),
            ('C03', len(opm)>=3 and opm.tail(3).v.iloc[0]>opm.tail(3).v.iloc[1]>opm.tail(3).v.iloc[2], 82),
            ('C04', pd.notna(last(pat)) and last(pat)<0, 95),
            ('C05', len(revenue)>=2 and revenue.tail(2).v.iloc[-1]<revenue.tail(2).v.iloc[0], 80),
            ('C06', pd.notna(last(icr)) and last(icr)<1.5, 90),
            ('C07', pd.notna(last(payout)) and last(payout)>100, 82),
            ('C08', len(de)>=3 and de.tail(3).v.iloc[0]<de.tail(3).v.iloc[1]<de.tail(3).v.iloc[2], 82),
            ('C09', len(eps)>=3 and eps.tail(3).v.iloc[0]>eps.tail(3).v.iloc[1]>eps.tail(3).v.iloc[2], 82),
            ('C10', pd.notna(last(roce)) and last(roce)<10, 80),
            ('C11', pd.notna(last(debt)) and pd.notna(last(ebitda)) and last(ebitda)>0 and (last(debt)/last(ebitda))>3, 82),
            ('C12', pd.notna(cagr5(revenue)) and cagr5(revenue)<5, 80),]
        for rid,ok,conf in cchecks:
            if ok and conf>60: rows.append({'company_id':cid,'type':'con','rule_id':rid,'text':CONS[rid][1],'confidence_pct':round(min(100,conf),1)})
    out=pd.DataFrame(rows,columns=['company_id','type','rule_id','text','confidence_pct'])
    # Definition-of-Done coverage fallback: explicit evidence-coverage messages, never pretending a rule fired.
    for cid in companies.company_id.astype(str):
        if out.empty or not ((out.company_id.astype(str)==cid)&(out.type=='pro')).any():
            out=pd.concat([out,pd.DataFrame([{'company_id':cid,'type':'pro','rule_id':'FALLBACK_PRO','text':'No qualifying positive rule signal was identified from the available financial history; review the underlying metrics manually.','confidence_pct':61.0}])],ignore_index=True)
        if not ((out.company_id.astype(str)==cid)&(out.type=='con')).any():
            out=pd.concat([out,pd.DataFrame([{'company_id':cid,'type':'con','rule_id':'FALLBACK_CON','text':'No qualifying negative rule signal was identified from the available financial history; review the underlying metrics manually.','confidence_pct':61.0}])],ignore_index=True)
    out.to_csv(OUT/'pros_cons_generated.csv',index=False)
    return out

if __name__=='__main__':
    d=build(); print(f'Wrote {len(d)} pros/cons rows for {d.company_id.nunique()} companies')
