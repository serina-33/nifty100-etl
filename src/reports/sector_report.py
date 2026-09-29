from pathlib import Path
import pandas as pd, numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from src.common import OUT, REPORTS, connect, company_table

def build():
    with connect() as con: companies=company_table(con)
    intel=pd.read_excel(OUT/'cashflow_intelligence.xlsx') if (OUT/'cashflow_intelligence.xlsx').exists() else pd.DataFrame()
    ratios=pd.read_sql_query('SELECT * FROM financial_ratios',connect())
    ratios.columns=[str(c).strip().lower() for c in ratios.columns]
    idc='company_id'; ratios[idc]=ratios[idc].astype(str); ratios['year']=pd.to_numeric(ratios['year'],errors='coerce') if 'year' in ratios else np.nan
    latest=ratios.sort_values('year').groupby(idc).tail(1) if not ratios.empty else pd.DataFrame()
    base=companies.copy(); base['company_id']=base.company_id.astype(str); base=base.merge(latest,on='company_id',how='left',suffixes=('','_ratio'))
    if not intel.empty: base=base.merge(intel,on='company_id',how='left',suffixes=('','_cf'))
    cols=[('ROE',['roe']),('ROCE',['roce']),('D/E',['de_ratio','debt_to_equity']),('OPM',['opm']),('FCF CAGR',['fcf_cagr_5yr']),('CFO Quality',['cfo_quality_score']),('CapEx %',['capex_intensity_pct']),('Capital Allocation',['capital_allocation_label'])]
    out=[]
    for sec,g in base.groupby('sector',dropna=False):
        secname=str(sec) if pd.notna(sec) else 'Unknown'; path=REPORTS/'sector'/f'{secname.replace("/","-").replace(" ","_")}_report.pdf'; doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=8*mm,leftMargin=8*mm,topMargin=8*mm,bottomMargin=8*mm); styles=getSampleStyleSheet(); story=[Paragraph(f'{secname} Sector Report',styles['Title']),Spacer(1,3*mm),Paragraph(f'Companies: {len(g)}',styles['BodyText']),Spacer(1,3*mm)]
        med=[]
        for label,cands in cols[:-1]:
            c=next((c for c in cands if c in g.columns),None)
            if c: med.append([label, f'{pd.to_numeric(g[c],errors="coerce").median():.2f}'])
        story.append(Paragraph('<b>Sector Median KPIs</b>',styles['Heading2'])); story.append(Table(med or [['No KPI data','']],colWidths=[55*mm,40*mm],style=[('GRID',(0,0),(-1,-1),.4,colors.lightgrey)])); story.append(Spacer(1,4*mm))
        header=['Ticker','Company','ROE','ROCE','D/E','OPM','FCF CAGR','CFO Q','CapEx %','Allocation']; data=[header]
        for _,r in g.sort_values('ticker').iterrows():
            def val(c):
                if c not in r.index or pd.isna(r[c]): return 'NA'
                return f'{r[c]:.2f}' if isinstance(r[c],(int,float,np.integer,np.floating)) else str(r[c])[:18]
            data.append([str(r.ticker),str(r.company_name)[:22],val('roe'),val('roce'),val('de_ratio') if 'de_ratio' in r else val('debt_to_equity'),val('opm'),val('fcf_cagr_5yr'),val('cfo_quality_score'),val('capex_intensity_pct'),val('capital_allocation_label')])
        story.append(Table([[Paragraph(str(x),styles['BodyText']) for x in row] for row in data],repeatRows=1,colWidths=[15*mm,39*mm,14*mm,14*mm,13*mm,13*mm,16*mm,15*mm,15*mm,25*mm],style=[('GRID',(0,0),(-1,-1),.3,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E9EEF6')),('FONTSIZE',(0,0),(-1,-1),6),('VALIGN',(0,0),(-1,-1),'TOP')]))
        doc.build(story); out.append(path)
    return out
if __name__=='__main__': print(f'Generated {len(build())} sector reports')
