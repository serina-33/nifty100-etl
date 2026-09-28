"""Sprint 3 Day 17 — screener Excel export."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"output"
GREEN=PatternFill("solid",fgColor="C6EFCE")
RED=PatternFill("solid",fgColor="FFC7CE")
HEADER=PatternFill("solid",fgColor="1F4E78")

DISPLAY_COLUMNS=[
 "company_id","company_name","ticker","sector","broad_sector","year",
 "roe","roce","npm","de","fcf","revenue_cagr_5yr","revenue_cagr_3yr",
 "pat_cagr_5yr","opm","pe","pb","dividend_yield","icr","market_cap_cr",
 "net_profit","eps_cagr_5yr","asset_turnover","sales","payout","composite_quality_score"
]
def _criteria(row, preset):
    tests=[]
    def g(k,op,v):
        x=row.get(k)
        if pd.isna(x): return False
        return op(x,v)
    if preset=="Quality Compounder":
        tests=[g("roe",lambda a,b:a>b,15),g("de",lambda a,b:a<b,1),g("fcf",lambda a,b:a> b,0),g("revenue_cagr_5yr",lambda a,b:a>b,10)]
    elif preset=="Value Pick":
        tests=[g("pe",lambda a,b:a<b,20),g("pb",lambda a,b:a<b,3),g("de",lambda a,b:a<b,2),g("dividend_yield",lambda a,b:a>b,1)]
    elif preset=="Growth Accelerator":
        tests=[g("pat_cagr_5yr",lambda a,b:a>b,20),g("revenue_cagr_5yr",lambda a,b:a>b,15),g("de",lambda a,b:a<b,2)]
    elif preset=="Dividend Champion":
        tests=[g("dividend_yield",lambda a,b:a>b,2),g("payout",lambda a,b:a<b,80),g("fcf",lambda a,b:a>b,0)]
    elif preset=="Debt-Free Blue Chip":
        tests=[g("de",lambda a,b:a==b,0),g("roe",lambda a,b:a>b,12),g("sales",lambda a,b:a>b,5000)]
    elif preset=="Turnaround Watch":
        tests=[g("revenue_cagr_3yr",lambda a,b:a>b,10),bool(row.get("fcf_positive",False)),bool(row.get("de_declining_yoy",False))]
    return tests

def export_screener_workbook(results:dict, path=OUT/"screener_output.xlsx"):
    path.parent.mkdir(parents=True,exist_ok=True)
    with pd.ExcelWriter(path,engine="openpyxl") as writer:
        for preset,df in results.items():
            cols=[c for c in DISPLAY_COLUMNS if c in df.columns]
            # Include useful extra score/flag columns while retaining a compact KPI report.
            extras=[c for c in ["payout","fcf_positive","de_declining_yoy","composite_quality_score"] if c in df.columns and c not in cols]
            data=df[cols+extras].copy()
            data.to_excel(writer,sheet_name=preset[:31],index=False)
    wb=load_workbook(path)
    for ws in wb.worksheets:
        for cell in ws[1]:
            cell.fill=HEADER; cell.font=Font(color="FFFFFF",bold=True)
        headers={c.value:c.column for c in ws[1]}
        preset=ws.title
        for r in range(2,ws.max_row+1):
            row={k:ws.cell(r,c).value for k,c in headers.items()}
            # Reconstruct a pandas-like row for criteria checks.
            flags=_criteria(row,preset)
            # If sheet values are strings/numbers, criteria still works.
            # Colour the relevant threshold cells.
            metric_names={
                "Quality Compounder":["roe","de","fcf","revenue_cagr_5yr"],
                "Value Pick":["pe","pb","de","dividend_yield"],
                "Growth Accelerator":["pat_cagr_5yr","revenue_cagr_5yr","de"],
                "Dividend Champion":["dividend_yield","payout","fcf"],
                "Debt-Free Blue Chip":["de","roe","sales"],
                "Turnaround Watch":["revenue_cagr_3yr","fcf","de"],
            }.get(preset,[])
            for i,metric in enumerate(metric_names):
                if metric in headers:
                    ws.cell(r,headers[metric]).fill=GREEN if (flags[i] if i<len(flags) else False) else RED
        ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
        for col in range(1,ws.max_column+1):
            letter=get_column_letter(col)
            maxlen=max(len(str(ws.cell(row,col).value or "")) for row in range(1,min(ws.max_row,100)+1))
            ws.column_dimensions[letter].width=min(max(maxlen+2,12),28)
    wb.save(path)
    return path
