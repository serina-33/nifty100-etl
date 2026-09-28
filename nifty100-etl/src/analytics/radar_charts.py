"""Sprint 3 Day 19 — peer radar chart generation."""
from __future__ import annotations
import sqlite3, math
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
DB_PATH=ROOT/"nifty100.db"
OUT=ROOT/"reports"/"radar_charts"
AXES=["ROE","ROCE","NPM","D/E","FCF Score","PAT CAGR 5yr","Revenue CAGR 5yr","Composite Score"]

def _scale_series(s, inverse=False):
    s=pd.to_numeric(s,errors="coerce")
    if s.notna().sum()<2: z=pd.Series(50.0,index=s.index)
    else:
        lo,hi=np.nanpercentile(s.dropna(),[10,90])
        z=pd.Series(50.0,index=s.index) if hi==lo else ((s.clip(lo,hi)-lo)/(hi-lo)*100)
    if inverse: z=100-z
    return z.fillna(50)

def _metrics(df):
    out=pd.DataFrame(index=df.index)
    out["ROE"]=_scale_series(df["return_on_equity_pct"])
    out["ROCE"]=_scale_series(df["return_on_capital_employed_pct"])
    out["NPM"]=_scale_series(df["net_profit_margin_pct"])
    out["D/E"]=_scale_series(df["debt_to_equity"],True)
    out["FCF Score"]=_scale_series(df["free_cash_flow_cr"])
    out["PAT CAGR 5yr"]=_scale_series(df["pat_cagr_5yr"])
    out["Revenue CAGR 5yr"]=_scale_series(df["revenue_cagr_5yr"])
    out["Composite Score"]=_scale_series(df["composite_quality_score"])
    return out

def generate_radar_charts(db_path=DB_PATH,out_dir=OUT,peer_assignments=None):
    out_dir.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(db_path)
    base=pd.read_sql_query("""SELECT fr.*,c.company_name,c.ticker,c.sector
        FROM financial_ratios fr JOIN companies c ON c.company_id=fr.company_id""",conn)
    usable=base[base[["net_profit_margin_pct","return_on_equity_pct","free_cash_flow_cr"]].notna().any(axis=1)]
    base=pd.concat([usable.sort_values("year").groupby("company_id",as_index=False).tail(1),
                    base.sort_values("year").groupby("company_id",as_index=False).tail(1)]
                   ).drop_duplicates("company_id",keep="first")
    conn.close()
    if peer_assignments is None or peer_assignments.empty:
        peer_assignments=pd.DataFrame({"company_id":base.company_id,"peer_group_name":"Nifty 100","is_benchmark":False})
    merged=base.merge(peer_assignments,on="company_id",how="left")
    merged["peer_group_name"]=merged["peer_group_name"].fillna("Nifty 100")
    metrics=_metrics(merged)
    merged=merged.join(metrics.add_prefix("_"),rsuffix="_metric")
    angles=np.linspace(0,2*np.pi,len(AXES),endpoint=False).tolist(); angles += angles[:1]
    paths=[]
    for _,r in merged.iterrows():
        group=merged[merged.peer_group_name==r.peer_group_name]
        gm=_metrics(group).mean(axis=0)
        vals=[r[f"_{a}"] for a in AXES]+[r[f"_{AXES[0]}"]]
        av=[gm[a] for a in AXES]+[gm[AXES[0]]]
        fig=plt.figure(figsize=(7,7))
        ax=fig.add_subplot(111,polar=True)
        ax.plot(angles,vals,linewidth=2)
        ax.fill(angles,vals,alpha=.20)
        ax.plot(angles,av,linestyle="--",linewidth=1.5)
        ax.set_xticks(angles[:-1]); ax.set_xticklabels(AXES,fontsize=9)
        ax.set_ylim(0,100); ax.set_yticks([25,50,75,100])
        ax.set_title(f"{r.company_name} — {r.peer_group_name}\nSolid = company | Dashed = peer average",pad=22)
        safe=str(r.ticker or r.company_name).replace("/","_").replace("\\","_").replace(" ","_")
        path=out_dir/f"{safe}_radar.png"
        fig.tight_layout(); fig.savefig(path,dpi=150,bbox_inches="tight"); plt.close(fig)
        paths.append(path)
    return paths
