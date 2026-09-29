import math, sqlite3, shutil
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
from reportlab.pdfbase.pdfmetrics import stringWidth
from src.common import ROOT, OUT, REPORTS, connect, company_table, load_financial, col, cagr

NAVY=colors.HexColor('#14213D'); GREEN=colors.HexColor('#2E7D32'); RED=colors.HexColor('#C62828'); GREY=colors.HexColor('#F2F4F7')
styles=getSampleStyleSheet(); body=ParagraphStyle('body',parent=styles['BodyText'],fontSize=8.5,leading=11); small=ParagraphStyle('small',parent=body,fontSize=7,leading=9); title=ParagraphStyle('title',parent=styles['Title'],fontSize=20,leading=23,textColor=colors.white)

def _one(df,cid,names):
    if df.empty:return pd.DataFrame(columns=['year','v'])
    d=df[df['_company_id'].eq(str(cid))].copy().sort_values('_year'); c=col(d,names)
    if c is None:return pd.DataFrame(columns=['year','v'])
    return pd.DataFrame({'year':pd.to_numeric(d['_year'],errors='coerce'),'v':pd.to_numeric(d[c],errors='coerce')}).dropna()

def _metric(fin,key,cid,names): return _one(fin[key],cid,names)

def _latest(s): return s.v.iloc[-1] if not s.empty else np.nan

def _chart_company(cid, fin, folder):
    pl=fin['pl']; bs=fin['bs']; cf=fin['cf']; r=fin['ratios']; paths={}
    rev=_metric(fin,'pl',cid,['revenue','sales','total_revenue']); pat=_metric(fin,'pl',cid,['net_profit','profit_after_tax','pat','net_profit_after_tax'])
    if not rev.empty or not pat.empty:
        y=sorted(set(rev.year.astype(int))|set(pat.year.astype(int))); a=rev.set_index('year').reindex(y).v; b=pat.set_index('year').reindex(y).v
        fig,ax=plt.subplots(figsize=(4.5,2.25)); x=np.arange(len(y)); w=.36; ax.bar(x-w/2,a.fillna(0),w,label='Revenue'); ax.bar(x+w/2,b.fillna(0),w,label='Net Profit'); ax.set_xticks(x); ax.set_xticklabels([str(int(i)) for i in y],rotation=45,fontsize=6); ax.tick_params(axis='y',labelsize=6); ax.legend(fontsize=6); ax.set_title('10-Year Revenue & Net Profit',fontsize=9); fig.tight_layout(); p=folder/f'{cid}_pl.png'; fig.savefig(p,dpi=160); plt.close(fig); paths['pl']=p
    roe=_metric(fin,'ratios',cid,['roe','return_on_equity']); roce=_metric(fin,'ratios',cid,['roce','return_on_capital_employed'])
    if not roe.empty or not roce.empty:
        y=sorted(set(roe.year.astype(int))|set(roce.year.astype(int))); fig,ax=plt.subplots(figsize=(4.5,2.25)); ax2=ax.twinx();
        if not roe.empty: q=roe.set_index('year').reindex(y); ax.plot(y,q.v,marker='o',label='ROE')
        if not roce.empty: q=roce.set_index('year').reindex(y); ax2.plot(y,q.v,marker='s',label='ROCE')
        ax.set_title('ROE / ROCE Trend',fontsize=9); ax.tick_params(labelsize=6); ax2.tick_params(labelsize=6); fig.tight_layout(); p=folder/f'{cid}_returns.png'; fig.savefig(p,dpi=160); plt.close(fig); paths['returns']=p
    assets=_metric(fin,'bs',cid,['total_assets','assets']); debt=_metric(fin,'bs',cid,['total_debt','borrowings','debt']); equity=_metric(fin,'bs',cid,['shareholders_equity','total_equity','equity']); liabilities=_metric(fin,'bs',cid,['other_liabilities','total_liabilities'])
    if any(not x.empty for x in [assets,debt,equity,liabilities]):
        y=sorted(set(sum([x.year.astype(int).tolist() for x in [assets,debt,equity,liabilities] if not x.empty],[]))); fig,ax=plt.subplots(figsize=(8.5,2.2)); bottom=np.zeros(len(y));
        for name,s in [('Equity',equity),('Borrowings',debt),('Other Liabilities',liabilities)]:
            if s.empty: continue
            vals=s.set_index('year').reindex(y).v.fillna(0).values; ax.bar(y,vals,bottom=bottom,label=name); bottom+=vals
        ax.set_title('Balance Sheet Composition',fontsize=9); ax.tick_params(labelsize=6); ax.legend(fontsize=6,ncol=3); fig.tight_layout(); p=folder/f'{cid}_bs.png'; fig.savefig(p,dpi=160); plt.close(fig); paths['bs']=p
    cfo=_metric(fin,'cf',cid,['cash_from_operations','cfo','net_cash_from_operating_activities']); cfi=_metric(fin,'cf',cid,['cash_from_investing','cfi','net_cash_from_investing_activities']); cff=_metric(fin,'cf',cid,['cash_from_financing','cff','net_cash_from_financing_activities'])
    if not cfo.empty or not cfi.empty or not cff.empty:
        latest=max([int(x.year.iloc[-1]) for x in [cfo,cfi,cff] if not x.empty]); vals=[_latest(cfo[cfo.year.eq(latest)]),_latest(cfi[cfi.year.eq(latest)]),_latest(cff[cff.year.eq(latest)])]; labels=['CFO','CFI','CFF','Net Cash Flow']; vals.append(sum(0 if pd.isna(v) else v for v in vals)); fig,ax=plt.subplots(figsize=(8.5,1.8)); ax.bar(labels,vals); ax.set_title(f'Cash Flow — Latest Year {latest}',fontsize=9); ax.tick_params(labelsize=7); fig.tight_layout(); p=folder/f'{cid}_cf.png'; fig.savefig(p,dpi=160); plt.close(fig); paths['cf']=p
    return paths

def _doc_styles():
    return body, ParagraphStyle('bulletg',parent=body,textColor=GREEN,leftIndent=8,bulletIndent=0), ParagraphStyle('bulletr',parent=body,textColor=RED,leftIndent=8,bulletIndent=0)

def build_company(cid, co, fin, pc, intel, outdir):
    outdir.mkdir(parents=True,exist_ok=True); tmp=outdir/'_charts'; tmp.mkdir(exist_ok=True); charts=_chart_company(cid,fin,tmp)
    path=outdir/f'{co.ticker}_tearsheet.pdf'; doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=10*mm,leftMargin=10*mm,topMargin=9*mm,bottomMargin=9*mm)
    story=[]; story.append(Table([[Paragraph(f'{co.company_name}  |  {co.ticker}',title)]],colWidths=[190*mm],rowHeights=[22*mm],style=[('BACKGROUND',(0,0),(-1,-1),NAVY),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),8)])); story.append(Spacer(1,5*mm))
    rr=fin['ratios']; latest=rr[rr._company_id.eq(cid)].sort_values('_year').tail(1) if not rr.empty else pd.DataFrame(); vals=[]
    kpis=[('ROE',['roe','return_on_equity']),('ROCE',['roce','return_on_capital_employed']),('D/E',['de_ratio','debt_to_equity','de']),('OPM',['opm','operating_profit_margin']),('EPS',['eps']),('P/E',['pe_ratio','pe'])]
    for label,names in kpis:
        c=col(latest,names); v=pd.to_numeric(latest[c],errors='coerce').iloc[-1] if c and not latest.empty else np.nan; vals.append([Paragraph(f'<b>{label}</b><br/>{"NA" if pd.isna(v) else f"{v:.2f}"}',body)])
    tiles=Table([vals[0:3],vals[3:6]],colWidths=[60*mm]*3,rowHeights=[20*mm]*2,style=[('BACKGROUND',(0,0),(-1,-1),GREY),('BOX',(0,0),(-1,-1),.5,colors.lightgrey),('INNERGRID',(0,0),(-1,-1),.5,colors.white),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(0,0),(-1,-1),'CENTER')]); story.append(tiles); story.append(Spacer(1,4*mm))
    if 'pl' in charts and 'returns' in charts: story.append(Table([[Image(str(charts['pl']),width=88*mm,height=44*mm),Image(str(charts['returns']),width=88*mm,height=44*mm)]],colWidths=[92*mm,92*mm]))
    story.append(PageBreak())
    if 'bs' in charts: story.append(Image(str(charts['bs']),width=178*mm,height=46*mm)); story.append(Spacer(1,3*mm))
    if 'cf' in charts: story.append(Image(str(charts['cf']),width=178*mm,height=38*mm)); story.append(Spacer(1,3*mm))
    pcd=pc[pc.company_id.astype(str).eq(cid)] if pc is not None and not pc.empty else pd.DataFrame(); pros=pcd[pcd.type.eq('pro')].head(5); cons=pcd[pcd.type.eq('con')].head(5)
    data=[]
    for _,x in pros.iterrows(): data.append([Paragraph('• '+str(x.text),_doc_styles()[1])])
    for _,x in cons.iterrows(): data.append([Paragraph('• '+str(x.text),_doc_styles()[2])])
    story.append(Paragraph('<b>Pros / Cons</b>',body)); story.append(Table(data or [[Paragraph('No generated signals available.',body)]],colWidths=[178*mm],style=[('VALIGN',(0,0),(-1,-1),'TOP'),('BOX',(0,0),(-1,-1),.4,colors.lightgrey),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)])); story.append(Spacer(1,3*mm))
    alloc='Not Available';
    if intel is not None and not intel.empty:
        q=intel[intel.company_id.astype(str).eq(cid)];
        if not q.empty: alloc=str(q.iloc[0].capital_allocation_label)
    story.append(Table([[Paragraph(f'<b>Capital Allocation: {alloc}</b>',body)]],colWidths=[178*mm],style=[('BACKGROUND',(0,0),(-1,-1),GREY),('BOX',(0,0),(-1,-1),.6,NAVY),('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    doc.build(story); return path

def build_all():
    with connect() as con: companies=company_table(con); fin=load_financial(con)
    pc=pd.read_csv(OUT/'pros_cons_generated.csv') if (OUT/'pros_cons_generated.csv').exists() else pd.DataFrame(); intel=pd.read_excel(OUT/'cashflow_intelligence.xlsx') if (OUT/'cashflow_intelligence.xlsx').exists() else pd.DataFrame()
    skip=[]; paths=[]
    for _,co in companies.iterrows():
        cid=str(co.company_id); all_years=set()
        for k in ['pl','bs','cf','ratios']:
            if not fin[k].empty: all_years.update(fin[k][fin[k]._company_id.eq(cid)]._year.dropna().astype(int).tolist())
        if len(all_years)<3: skip.append({'company_id':cid,'ticker':co.ticker,'reason':'less_than_3_years'}); continue
        paths.append(build_company(cid,co,fin,pc,intel,REPORTS/'tearsheets'))
    pd.DataFrame(skip).to_csv(OUT/'skipped_tearsheets.csv',index=False)
    # remove chart temp files
    shutil.rmtree(REPORTS/'tearsheets'/'_charts',ignore_errors=True)
    return paths

if __name__=='__main__':
    ps=build_all(); print(f'Generated {len(ps)} company tearsheets')
