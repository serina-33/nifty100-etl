from pathlib import Path
import py_compile, sqlite3
import pandas as pd
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]; errors=[]
files=['src/common.py','src/nlp/parser.py','src/nlp/pros_cons_generator.py','src/analytics/cashflow_kpis.py','src/analytics/capital_allocation.py','src/reports/tearsheet.py','src/reports/sector_report.py','src/reports/portfolio_summary.py','scripts/run_sprint5.py']
for f in files:
    try: py_compile.compile(str(ROOT/f),doraise=True)
    except Exception as e: errors.append(f'compile {f}: {e}')
with sqlite3.connect(ROOT/'nifty100.db') as con:
    n=con.execute('select count(*) from companies').fetchone()[0]
if n!=92: errors.append(f'Expected 92 companies, found {n}')
pc=ROOT/'output/pros_cons_generated.csv'; ai=ROOT/'output/analysis_parsed.csv'; ci=ROOT/'output/cashflow_intelligence.xlsx'
if not pc.exists(): errors.append('Missing pros_cons_generated.csv')
else:
 d=pd.read_csv(pc); ids=d.company_id.astype(str); c=pd.read_sql_query('select company_id from companies',sqlite3.connect(ROOT/'nifty100.db')).company_id.astype(str); 
 if set(c)-set(ids[d.type.eq('pro')]): errors.append('Companies missing pro signal')
 if set(c)-set(ids[d.type.eq('con')]): errors.append('Companies missing con signal')
if not ai.exists(): errors.append('Missing analysis_parsed.csv')
if not ci.exists(): errors.append('Missing cashflow_intelligence.xlsx')
else:
 d=pd.read_excel(ci)
 req=['company_id','sector','cfo_quality_score','cfo_quality_label','capex_intensity_pct','capex_label','fcf_cagr_5yr','fcf_conversion_pct','distress_flag','deleveraging_flag','capital_allocation_label']
 if len(d)!=92: errors.append(f'Cashflow rows={len(d)}, expected 92')
 if any(x not in d.columns for x in req): errors.append('Cashflow required columns missing')
tee=list((ROOT/'reports/tearsheets').glob('*_tearsheet.pdf')); tee=[p for p in tee if p.name!='_tearsheet.pdf']
if len(tee)!=92:
 # allow skipped count, but skipped file documents it
 sk=pd.read_csv(ROOT/'output/skipped_tearsheets.csv') if (ROOT/'output/skipped_tearsheets.csv').exists() else pd.DataFrame()
 if len(tee)!=92-len(sk): errors.append(f'Tearsheet count={len(tee)}; expected {92-len(sk)}')
for p in tee:
 if p.stat().st_size<30*1024: errors.append(f'Tearsheet <30KB: {p.name}')
 try:
  pages=len(PdfReader(str(p)).pages)
  if pages!=2: errors.append(f'Tearsheet pages !=2: {p.name} ({pages})')
 except Exception as e: errors.append(f'Unreadable PDF {p.name}: {e}')
sec=list((ROOT/'reports/sector').glob('*_report.pdf'))
if len(sec)!=11: errors.append(f'Sector PDF count={len(sec)}, expected 11')
port=ROOT/'reports/portfolio/portfolio_summary.pdf'
if not port.exists(): errors.append('Missing portfolio_summary.pdf')
else:
 pages=len(PdfReader(str(port)).pages)
 if pages!=92: errors.append(f'Portfolio pages={pages}, expected 92')
print('Companies:',n); print('Tearsheets:',len(tee)); print('Sector PDFs:',len(sec)); print('Portfolio PDF:',port.exists())
if errors:
 print('\nFAIL'); [print(' -',e) for e in errors]; raise SystemExit(1)
print('Sprint 5 verification: PASS')
