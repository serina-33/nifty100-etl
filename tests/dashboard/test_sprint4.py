from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]

def test_dashboard_files_exist():
    assert (ROOT/'src/dashboard/app.py').exists()
    for n in ['home','profile','screener','peers','trends','sectors','capital','reports']:
        assert (ROOT/f'src/dashboard/pages/{list(range(1,9))[['home','profile','screener','peers','trends','sectors','capital','reports'].index(n)]:02d}_{n}.py').exists()

def test_valuation_columns_if_generated():
    p=ROOT/'output/valuation_summary.xlsx'
    if not p.exists(): return
    d=pd.read_excel(p); required=['company_id','company_name','sector','P/E','P/B','EV/EBITDA','FCF_yield_pct','5yr_median_PE','PE_vs_sector_median_pct','flag']
    assert set(required).issubset(d.columns)
    assert len(d)==92
