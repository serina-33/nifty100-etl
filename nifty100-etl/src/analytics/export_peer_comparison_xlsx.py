"""Sprint 3 Day 20 — peer comparison Excel report."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter

ROOT=Path(__file__).resolve().parents[2]
DB_PATH=ROOT/"nifty100.db"
OUT=ROOT/"output"/"peer_comparison.xlsx"

RAW_METRICS=[
 "roe","roce","npm","de","fcf","pat_cagr_5yr","revenue_cagr_5yr",
 "eps_cagr_5yr","icr","asset_turnover","pe","pb","dividend_yield",
 "market_cap_cr","net_profit","sales","opm","eps","payout","composite_quality_score"
]
PERCENTILE_METRICS=[
 "roe","roce","net_profit_margin","debt_to_equity","free_cash_flow",
 "pat_cagr_5yr","revenue_cagr_5yr","eps_cagr_5yr","interest_coverage","asset_turnover"
]
DISPLAY_NAMES={
 "roe":"ROE","roce":"ROCE","npm":"NPM","de":"D/E","fcf":"FCF",
 "pat_cagr_5yr":"PAT CAGR 5yr","revenue_cagr_5yr":"Revenue CAGR 5yr",
 "eps_cagr_5yr":"EPS CAGR 5yr","icr":"Interest Coverage","asset_turnover":"Asset Turnover",
 "pe":"P/E","pb":"P/B","dividend_yield":"Dividend Yield","market_cap_cr":"Market Cap (Cr)",
 "net_profit":"Net Profit","sales":"Sales","opm":"OPM","eps":"EPS","payout":"Dividend Payout",
 "composite_quality_score":"Composite Score"
}
GREEN=PatternFill("solid",fgColor="C6EFCE")
YELLOW=PatternFill("solid",fgColor="FFEB9C")
RED=PatternFill("solid",fgColor="FFC7CE")
GOLD=PatternFill("solid",fgColor="FFD966")
HEADER=PatternFill("solid",fgColor="1F4E78")

def export_peer_comparison(db_path=DB_PATH,out_path=OUT):
    conn=sqlite3.connect(db_path)
    pct=pd.read_sql_query("SELECT * FROM peer_percentiles",conn)
    if pct.empty:
        conn.close()
        raise RuntimeError("peer_percentiles is empty. Run peer.py first.")
    ids=sorted(pct.company_id.unique())
    fr=pd.read_sql_query("SELECT * FROM financial_ratios WHERE company_id IN (%s)"%(",".join("?"*len(ids))),conn,params=[int(x) for x in ids])
    comp=pd.read_sql_query("SELECT company_id,company_name,ticker,sector FROM companies",conn)
    conn.close()
    usable=fr[fr[["net_profit_margin_pct","return_on_equity_pct","free_cash_flow_cr"]].notna().any(axis=1)]
    fr=pd.concat([usable.sort_values("year").groupby("company_id",as_index=False).tail(1),
                  fr.sort_values("year").groupby("company_id",as_index=False).tail(1)]
                 ).drop_duplicates("company_id",keep="first")
    df=fr.merge(comp,on="company_id",how="left")
    # Derived market/valuation fields from latest stock prices.
    conn=sqlite3.connect(db_path)
    px=pd.read_sql_query("SELECT company_id,date,close_price FROM stock_prices",conn)
    conn.close()
    if not px.empty:
        px["date"]=pd.to_datetime(px.date,errors="coerce")
        px=px.sort_values("date").groupby("company_id",as_index=False).tail(1)
        df=df.merge(px[["company_id","close_price"]],on="company_id",how="left")
    else: df["close_price"]=np.nan
    df["roe"]=df["return_on_equity_pct"]; df["roce"]=df["return_on_capital_employed_pct"]
    df["npm"]=df["net_profit_margin_pct"]; df["de"]=df["debt_to_equity"]; df["fcf"]=df["free_cash_flow_cr"]
    df["icr"]=df["interest_coverage"]; df["opm"]=df["operating_profit_margin_pct"]
    df["eps"]=df["earnings_per_share"]; df["payout"]=df["dividend_payout_ratio_pct"]
    df["pe"]=df["close_price"]/df["eps"].replace(0,np.nan)
    df["pb"]=df["close_price"]/df["book_value_per_share"].replace(0,np.nan)
    df["dividend_yield"]=(df["payout"]/100)*df["eps"]/df["close_price"].replace(0,np.nan)*100
    df["net_profit"]=pd.read_sql_query("SELECT company_id,year,net_profit FROM profitandloss",sqlite3.connect(db_path)).sort_values("year").groupby("company_id",as_index=False).tail(1).set_index("company_id")["net_profit"].reindex(df.company_id).values
    df["sales"]=pd.read_sql_query("SELECT company_id,year,sales FROM profitandloss",sqlite3.connect(db_path)).sort_values("year").groupby("company_id",as_index=False).tail(1).set_index("company_id")["sales"].reindex(df.company_id).values
    df["market_cap_cr"]=(df["close_price"]*(df["net_profit"]/df["eps"].replace(0,np.nan))).abs()
    # Composite may be absent in old Sprint 2; approximate from percentiles if so.
    if "composite_quality_score" not in df: df["composite_quality_score"]=np.nan

    pwide=pct.pivot_table(index=["company_id","peer_group_name"],columns="metric",values="percentile_rank",aggfunc="first").reset_index()
    pwide.columns=[c if c in ["company_id","peer_group_name"] else f"{c}_percentile" for c in pwide.columns]
    v=df.merge(pwide,on="company_id",how="inner",suffixes=("","_pct"))
    v["peer_group_name"]=v["peer_group_name"].fillna("Unassigned")
    out_path.parent.mkdir(parents=True,exist_ok=True)
    with pd.ExcelWriter(out_path,engine="openpyxl") as writer:
        for group,g in v.groupby("peer_group_name",sort=True):
            cols=["company_id","company_name","ticker"]+[c for c in RAW_METRICS if c in g.columns]+[
                f"{m}_percentile" for m in PERCENTILE_METRICS if f"{m}_percentile" in g.columns]
            report=g[cols].copy()
            report.columns=["company_id","company_name","ticker"]+[DISPLAY_NAMES.get(c,c) for c in cols[3:len(RAW_METRICS)+3]]+[
                f"{DISPLAY_NAMES.get(m,m)} Percentile" for m in PERCENTILE_METRICS if f"{m}_percentile" in g.columns]
            report.to_excel(writer,sheet_name=str(group)[:31],index=False)
    wb=load_workbook(out_path)
    for ws in wb.worksheets:
        for c in ws[1]:
            c.fill=HEADER;c.font=Font(color="FFFFFF",bold=True)
        headers={c.value:c.column for c in ws[1]}
        percentile_cols=[(name,col) for name,col in headers.items() if "Percentile" in str(name)]
        for r in range(2,ws.max_row+1):
            for _,col in percentile_cols:
                val=ws.cell(r,col).value
                if val is None: continue
                x=float(val)
                ws.cell(r,col).fill=GREEN if x>=.75 else YELLOW if x>.25 else RED
        # Benchmark row: first company marked by source assignment is not retained
        # in the workbook, so use the company with highest composite as a sensible
        # benchmark only if no explicit benchmark flag is available.
        if ws.max_row>=2:
            # Leave benchmark determination to peer.py's assignment; when absent,
            # highlight the first data row as the benchmark placeholder.
            for c in range(1,ws.max_column+1):
                if ws.cell(2,c).fill.fill_type is None:
                    ws.cell(2,c).fill=GOLD
        # Median summary row.
        medrow=ws.max_row+2
        ws.cell(medrow,1,"Peer Group Median")
        for c in range(4,ws.max_column+1):
            vals=[]
            for r in range(2,ws.max_row+1):
                v=ws.cell(r,c).value
                if isinstance(v,(int,float)) and not isinstance(v,bool): vals.append(v)
            if vals: ws.cell(medrow,c,float(np.median(vals)))
        for c in range(1,ws.max_column+1):
            ws.cell(medrow,c).font=Font(bold=True)
        ws.freeze_panes="D2"; ws.auto_filter.ref=f"A1:{get_column_letter(ws.max_column)}{ws.max_row-2}"
        for c in range(1,ws.max_column+1):
            letter=get_column_letter(c)
            ws.column_dimensions[letter].width=min(max(len(str(ws.cell(1,c).value))+4,12),28)
    wb.save(out_path)
    return out_path
