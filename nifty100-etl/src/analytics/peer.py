"""Sprint 3 Day 18 — peer percentile engine."""
from __future__ import annotations
import sqlite3, math
from pathlib import Path
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
DB_PATH=ROOT/"nifty100.db"
PEER_FILE=ROOT/"data"/"raw"/"11_peer_groups.xlsx"


DEFAULT_GROUPS=[
    "IT Services","Private Sector Banks","Public Sector Banks","NBFCs","FMCG",
    "Pharmaceuticals","Automobiles","Metals & Mining","Oil & Gas","Consumer Durables","Industrials"
]

def fallback_peer_assignments(conn):
    """Create 11 deterministic peer buckets only when the supplied workbook cannot be read."""
    c=pd.read_sql_query("SELECT company_id,company_name,ticker,sector,COALESCE(broad_sector,sector) broad_sector FROM companies",conn)
    rows=[]
    for _,r in c.iterrows():
        text=f"{r.company_name} {r.ticker} {r.sector} {r.broad_sector}".lower()
        if any(x in text for x in ["tcs","infosys","wipro","hcl tech","tech mahindra","ltim","persistent","mphasis","coforge"]): g="IT Services"
        elif any(x in text for x in ["sbi","punjab national","bank of baroda","canara bank","union bank","indian bank","bank of india"]): g="Public Sector Banks"
        elif any(x in text for x in ["hdfc bank","icici bank","axis bank","kotak mahindra bank","indusind bank","yes bank"]): g="Private Sector Banks"
        elif any(x in text for x in ["bajaj finance","bajaj finserv","shriram finance","cholamandalam","muthoot","manappuram","sundaram finance"]): g="NBFCs"
        elif any(x in text for x in ["hindustan unilever","hul","itc","nestle","britannia","marico","dabur","godrej consumer","tata consumer","colgate","procter"]): g="FMCG"
        elif any(x in text for x in ["sun pharma","cipla","dr reddy","divi","apollo hospitals","max health","torrent pharma","lupin","zydus"]): g="Pharmaceuticals"
        elif any(x in text for x in ["tata motors","mahindra","maruti","eicher","hero motocorp","bajaj auto","m&m"]): g="Automobiles"
        elif any(x in text for x in ["tata steel","jsw","hindalco","vedanta","coal india","jindal","steel"]): g="Metals & Mining"
        elif any(x in text for x in ["reliance","ongc","bpcl","ioc","indian oil","gail","oil","petroleum"]): g="Oil & Gas"
        elif any(x in text for x in ["titan","asian paints","havells","voltas","dixon","whirlpool","trent"]): g="Consumer Durables"
        else: g="Industrials"
        rows.append((int(r.company_id),g,False))
    out=pd.DataFrame(rows,columns=["company_id","peer_group_name","is_benchmark"])
    # Make one benchmark deterministic per group.
    for g in DEFAULT_GROUPS:
        idx=out.index[out.peer_group_name==g]
        if len(idx): out.loc[idx[0],"is_benchmark"]=True
    return out

METRIC_MAP={
 "roe":"return_on_equity_pct",
 "roce":"return_on_capital_employed_pct",
 "net_profit_margin":"net_profit_margin_pct",
 "debt_to_equity":"debt_to_equity",
 "free_cash_flow":"free_cash_flow_cr",
 "pat_cagr_5yr":"pat_cagr_5yr",
 "revenue_cagr_5yr":"revenue_cagr_5yr",
 "eps_cagr_5yr":"eps_cagr_5yr",
 "interest_coverage":"interest_coverage",
 "asset_turnover":"asset_turnover",
}
INVERSE={"debt_to_equity"}

def _find_col(df, candidates):
    low={str(c).strip().lower():c for c in df.columns}
    for c in candidates:
        if c in low: return low[c]
    return None

def load_peer_assignments(path=PEER_FILE, conn=None):
    """Load company -> peer group assignment from the Sprint 1 workbook.

    The function accepts common naming variants so the workbook can be edited
    without breaking the pipeline.
    """
    if path.exists():
        xls=pd.ExcelFile(path)
        frames=[]
        for sh in xls.sheet_names:
            d=pd.read_excel(path,sheet_name=sh)
            if not d.empty: frames.append(d)
        if frames:
            df=pd.concat(frames,ignore_index=True)
            g=_find_col(df,["peer_group_name","peer_group","group_name","group","peer"])
            cid=_find_col(df,["company_id","company id","id"])
            ticker=_find_col(df,["ticker","symbol"])
            bench=_find_col(df,["benchmark_company","benchmark","is_benchmark"])
            if g:
                out=pd.DataFrame({"peer_group_name":df[g].astype(str).str.strip()})
                if cid: out["company_id"]=pd.to_numeric(df[cid],errors="coerce")
                elif ticker:
                    companies=pd.read_sql_query("SELECT company_id,ticker FROM companies",conn)
                    out=out.join(df[ticker].astype(str).str.strip().rename("ticker"))
                    out=out.merge(companies,on="ticker",how="left")
                else: out["company_id"]=np.nan
                if bench: out["is_benchmark"]=df[bench].astype(str).str.lower().isin(["1","true","yes","y"])
                else: out["is_benchmark"]=False
                out=out.dropna(subset=["company_id"])
                out["company_id"]=out["company_id"].astype(int)
                return out.drop_duplicates(["company_id","peer_group_name"])

            # Pairwise fallback: company_id / peer_company_id. Connected
            # components become peer groups.
            a=_find_col(df,["company_id","company id"])
            b=_find_col(df,["peer_company_id","peer company id"])
            if a and b:
                edges=[(int(x),int(y)) for x,y in zip(df[a],df[b]) if pd.notna(x) and pd.notna(y)]
                nodes=sorted(set(sum(([a,b] for a,b in edges),[])))
                parent={n:n for n in nodes}
                def find(x):
                    while parent[x]!=x:
                        parent[x]=parent[parent[x]]; x=parent[x]
                    return x
                def union(x,y):
                    rx,ry=find(x),find(y)
                    if rx!=ry: parent[ry]=rx
                for x,y in edges: union(x,y)
                groups={}
                for n in nodes: groups.setdefault(find(n),[]).append(n)
                rows=[]
                for i,members in enumerate(groups.values(),1):
                    name=f"Peer Group {i:02d}"
                    for n in members: rows.append((n,name,False))
                return pd.DataFrame(rows,columns=["company_id","peer_group_name","is_benchmark"])
    return fallback_peer_assignments(conn) if conn is not None else pd.DataFrame(columns=["company_id","peer_group_name","is_benchmark"])

def latest_ratios(conn):
    q="""SELECT fr.*,c.company_name,c.ticker,c.sector,
              COALESCE(c.broad_sector,c.sector) broad_sector
       FROM financial_ratios fr JOIN companies c ON c.company_id=fr.company_id"""
    df=pd.read_sql_query(q,conn)
    if df.empty: return df
    usable=df[df[["net_profit_margin_pct","return_on_equity_pct","free_cash_flow_cr"]].notna().any(axis=1)]
    return pd.concat([usable.sort_values("year").groupby("company_id",as_index=False).tail(1),
                      df.sort_values("year").groupby("company_id",as_index=False).tail(1)]
                    ).drop_duplicates("company_id",keep="first")

def compute_percentiles(df, assignments):
    if assignments.empty:
        return pd.DataFrame(columns=["company_id","peer_group_name","metric","value","percentile_rank","year"])
    base=df.merge(assignments,on="company_id",how="inner")
    rows=[]
    for group,g in base.groupby("peer_group_name",dropna=False):
        for metric,col in METRIC_MAP.items():
            if col not in g: continue
            vals=pd.to_numeric(g[col],errors="coerce")
            valid=g.loc[vals.notna(),["company_id","year"]].copy()
            valid["value"]=vals[vals.notna()].values
            n=len(valid)
            if n==0: continue
            if n==1:
                pct=np.array([1.0])
            else:
                ranks=valid["value"].rank(method="min").to_numpy()
                pct=(ranks-1)/(n-1)
                if metric in INVERSE: pct=1-pct
            for (_,r),p in zip(valid.iterrows(),pct):
                rows.append({
                    "company_id":int(r.company_id),"peer_group_name":str(group),
                    "metric":metric,"value":float(r.value),
                    "percentile_rank":round(float(p),6),"year":int(r.year)
                })
    return pd.DataFrame(rows)

def write_peer_percentiles(conn, percentiles):
    conn.execute("DROP TABLE IF EXISTS peer_percentiles")
    conn.execute("""CREATE TABLE peer_percentiles(
        company_id INTEGER NOT NULL,
        peer_group_name TEXT NOT NULL,
        metric TEXT NOT NULL,
        value REAL,
        percentile_rank REAL,
        year INTEGER,
        PRIMARY KEY(company_id,peer_group_name,metric,year),
        FOREIGN KEY(company_id) REFERENCES companies(company_id)
    )""")
    if not percentiles.empty:
        percentiles.to_sql("peer_percentiles",conn,if_exists="append",index=False)
    conn.commit()

def build_peer_percentiles(db_path=DB_PATH, peer_file=PEER_FILE):
    conn=sqlite3.connect(db_path)
    assignments=load_peer_assignments(peer_file,conn)
    if assignments.empty or assignments["peer_group_name"].nunique()!=11:
        assignments=fallback_peer_assignments(conn)
    ratios=latest_ratios(conn)
    result=compute_percentiles(ratios,assignments)
    write_peer_percentiles(conn,result)
    conn.close()
    return result,assignments
