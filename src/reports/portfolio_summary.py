import numpy as np, pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from src.common import OUT, REPORTS, connect, company_table, load_financial, col

def _latest_pair(df,cid,names):
    if df.empty:return np.nan,np.nan
    d=df[df['_company_id'].eq(str(cid))].sort_values('_year'); c=col(d,names)
    if c is None or len(d)<2:return np.nan,np.nan
    return pd.to_numeric(d[c].iloc[-1],errors='coerce'),pd.to_numeric(d[c].iloc[-2],errors='coerce')

def arrow(a,b):
    if pd.isna(a) or pd.isna(b): return '→'
    if b==0: return '↑' if a>0 else ('↓' if a<0 else '→')
    pct=(a/b-1)*100
    return '↑' if pct>2 else ('↓' if pct<-2 else '→')

def build():
    with connect() as con: companies=company_table(con); fin=load_financial(con)
    intel=pd.read_excel(OUT/'cashflow_intelligence.xlsx') if (OUT/'cashflow_intelligence.xlsx').exists() else pd.DataFrame(); pc=pd.read_csv(OUT/'pros_cons_generated.csv') if (OUT/'pros_cons_generated.csv').exists() else pd.DataFrame()
    path=REPORTS/'portfolio'/'portfolio_summary.pdf'; doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=10*mm,leftMargin=10*mm,topMargin=10*mm,bottomMargin=10*mm); st=getSampleStyleSheet(); story=[]
    for i,co in companies.sort_values('ticker').iterrows():
        story.append(Paragraph(f'{co.ticker} — {co.company_name}',st['Title'])); story.append(Paragraph(f'Sector: {co.sector}',st['Heading3']))
        kpis=[('ROE',['roe','return_on_equity']),('ROCE',['roce','return_on_capital_employed']),('D/E',['de_ratio','debt_to_equity','de']),('OPM',['opm','operating_profit_margin']),('P/E',['pe_ratio','pe']),('CFO Quality',None)]
        data=[['KPI','Latest','Trend']]
        for name,names in kpis:
            if names is None:
                if intel.empty or co.company_id not in intel.company_id.astype(str).values: a=b=np.nan
                else: a=float(intel[intel.company_id.astype(str).eq(str(co.company_id))].cfo_quality_score.iloc[0]); b=np.nan
            else: a,b=_latest_pair(fin['ratios'],co.company_id,names)
            data.append([name,'NA' if pd.isna(a) else f'{a:.2f}',arrow(a,b)])
        story.append(Table(data,colWidths=[55*mm,55*mm,35*mm],style=[('GRID',(0,0),(-1,-1),.4,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E9EEF6')),('FONTSIZE',(0,0),(-1,-1),9)])); story.append(Spacer(1,5*mm))
        alloc='NA';
        if not intel.empty:
            q=intel[intel.company_id.astype(str).eq(str(co.company_id))]; alloc=str(q.capital_allocation_label.iloc[0]) if not q.empty else 'NA'
        story.append(Paragraph(f'<b>Capital Allocation:</b> {alloc}',st['BodyText']))
        if i != companies.sort_values('ticker').index[-1]: story.append(PageBreak())
    doc.build(story); return path
if __name__=='__main__': print(build())
