from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
STEPS=[
 ('Parse analysis', [sys.executable,'-m','src.nlp.parser']),
 ('Generate pros/cons', [sys.executable,'-m','src.nlp.pros_cons_generator']),
 ('Cash flow intelligence', [sys.executable,'-m','src.analytics.cashflow_kpis']),
 ('Capital allocation', [sys.executable,'-m','src.analytics.capital_allocation']),
 ('Company tearsheets', [sys.executable,'-m','src.reports.tearsheet']),
 ('Sector reports', [sys.executable,'-m','src.reports.sector_report']),
 ('Portfolio summary', [sys.executable,'-m','src.reports.portfolio_summary']),
 ('Sprint 5 verification', [sys.executable,'scripts/verify_sprint5.py']),
]
for name,cmd in STEPS:
 print('\n'+'='*72+'\n'+name+'\n'+'='*72); subprocess.run(cmd,cwd=ROOT,check=True)
print('\nSPRINT 5 COMPLETE')
