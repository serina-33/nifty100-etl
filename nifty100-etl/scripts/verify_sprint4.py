from pathlib import Path
import sqlite3, py_compile
ROOT=Path(__file__).resolve().parents[1]
required=[ROOT/'src/dashboard/app.py']+[ROOT/f'src/dashboard/pages/{i:02d}_{n}.py' for i,n in enumerate(['home','profile','screener','peers','trends','sectors','capital','reports'],1)]+[ROOT/'src/dashboard/utils/db.py',ROOT/'src/analytics/valuation.py']
for p in required: py_compile.compile(str(p),doraise=True)
with sqlite3.connect(ROOT/'nifty100.db') as con:
    n=con.execute('select count(*) from companies').fetchone()[0]
print(f'Companies: {n}'); print('Python compile check: PASS'); print('Sprint 4 source files: PASS')
