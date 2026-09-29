"""Sprint 6 KMeans clustering, profiling, correlations and outliers."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy.stats import zscore
from src.common import OUT, REPORTS, connect, company_table, load_financial, latest_by_company, col, numeric

FEATURES = {
    'return_on_equity_pct':['return_on_equity_pct','roe_percentage','roe_pct','roe'],
    'debt_to_equity':['debt_to_equity','debt_equity','de_ratio','debt_to_equity_ratio'],
    'revenue_cagr_5yr':['revenue_cagr_5yr','sales_cagr_5yr','revenue_cagr'],
    'fcf_cagr_5yr':['fcf_cagr_5yr','free_cash_flow_cagr_5yr','fcf_cagr'],
    'operating_profit_margin_pct':['operating_profit_margin_pct','opm_pct','operating_margin_pct','opm'],
}


def _features():
    """Build the company feature matrix and sector medians."""
    con = connect(); comps = company_table(con); ratios = load_financial(con)['ratios']; con.close()
    latest = latest_by_company(ratios)
    m = comps.merge(latest, left_on='company_id', right_on='_company_id', how='left', suffixes=('','_ratio'))
    for out, aliases in FEATURES.items():
        c = col(m, aliases); m[out] = numeric(m,c) if c else np.nan
    for f in FEATURES:
        m[f] = m.groupby('broad_sector')[f].transform(lambda s: s.fillna(s.median()))
        m[f] = m[f].fillna(m[f].median()).fillna(0)
    return m


def run_clustering():
    """Fit five reproducible KMeans clusters and save labels and profiling outputs."""
    m = _features(); X = m[list(FEATURES)]
    scaler = StandardScaler(); Xs = scaler.fit_transform(X)
    inertias=[]
    for k in range(2,11): inertias.append(KMeans(n_clusters=k, random_state=42, n_init=20).fit(Xs).inertia_)
    REPORTS.mkdir(exist_ok=True)
    plt.figure(figsize=(8,5)); plt.plot(range(2,11), inertias, marker='o'); plt.xlabel('k'); plt.ylabel('Inertia'); plt.title('KMeans Elbow Plot'); plt.xticks(range(2,11)); plt.tight_layout(); plt.savefig(REPORTS/'elbow_plot.png', dpi=160); plt.close()
    model=KMeans(n_clusters=5, random_state=42, n_init=20); labels=model.fit_predict(Xs); dist=np.linalg.norm(Xs-model.cluster_centers_[labels],axis=1)
    out=m[['company_id','ticker','company_name','broad_sector']].copy(); out['cluster_id']=labels; out['distance_from_centroid']=dist
    profiles=pd.DataFrame(X).groupby(pd.Series(labels,name='cluster_id')).agg(['mean','median']).reset_index()
    profiles.to_csv(OUT/'cluster_profiles.csv', index=False)
    # Names are assigned from cluster statistics, then written consistently.
    stats=out.assign(**{f:m[f].values for f in FEATURES}).groupby('cluster_id')[list(FEATURES)].mean()
    names={}
    for cid,r in stats.iterrows():
        if r['return_on_equity_pct']>=20 and r['revenue_cagr_5yr']>=12 and r['fcf_cagr_5yr']>=8: n='High-Quality Compounders'
        elif r['return_on_equity_pct']>=15 and r['operating_profit_margin_pct']>=18 and r['debt_to_equity']<=1: n='Defensive Quality Leaders'
        elif r['revenue_cagr_5yr']>=15 and r['return_on_equity_pct']<15: n='Emerging Growth'
        elif r['debt_to_equity']>=2 or r['return_on_equity_pct']<8: n='Distressed or Turnaround'
        else: n='Value Cyclicals'
        names[int(cid)]=n
    out['cluster_name']=out['cluster_id'].map(names)
    out[['company_id','cluster_id','cluster_name','distance_from_centroid']].to_csv(OUT/'cluster_labels.csv', index=False)
    return out, m, names


def profile_statistics(m=None, labels=None):
    """Generate cluster statistics, ten-KPI correlation heatmap and outlier report."""
    if m is None: _,m,_=run_clustering()
    if labels is None: labels=pd.read_csv(OUT/'cluster_labels.csv')
    mm=m.merge(labels[['company_id','cluster_id']],on='company_id',how='left')
    rows=[]
    for cid,g in mm.groupby('cluster_id'):
        row={'cluster_id':cid,'company_count':len(g)}
        for f in FEATURES: row[f'{f}_mean']=g[f].mean(); row[f'{f}_median']=g[f].median()
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUT/'cluster_statistics.csv',index=False)
    # Ten KPI correlation matrix: use available ratio metrics first, then the five cluster features.
    con=connect(); ratios=load_financial(con)['ratios']; con.close(); latest=latest_by_company(ratios)
    aliases=[['return_on_equity_pct','roe_percentage','roe_pct','roe'],['roce_percentage','roce_pct','roce'],['debt_to_equity','debt_equity','de_ratio'],['revenue_cagr_5yr','sales_cagr_5yr'],['fcf_cagr_5yr','fcf_cagr'],['operating_profit_margin_pct','opm_pct','opm'],['pe','price_to_earnings','pe_ratio'],['pb','price_to_book','pb_ratio'],['dividend_yield','dividend_yield_pct'],['interest_coverage_ratio','icr']]
    corr=pd.DataFrame(index=range(len(latest)))
    for i,a in enumerate(aliases):
        c=col(latest,a); corr[f'KPI_{i+1}']=numeric(latest,c) if c else np.nan
    plt.figure(figsize=(10,8)); import seaborn as sns; sns.heatmap(corr.corr(method='pearson'),annot=True,fmt='.2f',square=True); plt.title('Pearson Correlation — 10 KPIs'); plt.tight_layout(); plt.savefig(REPORTS/'correlation_heatmap.png',dpi=160); plt.close()
    out=[]
    for f in FEATURES:
        z=mm.groupby('broad_sector')[f].transform(lambda s: zscore(s,nan_policy='omit'))
        mm[f'{f}_z']=z
    for _,r in mm.iterrows():
        bad=[f for f in FEATURES if pd.notna(r[f'{f}_z']) and abs(r[f'{f}_z'])>3]
        if bad: out.append({'company_id':r.company_id,'ticker':r.ticker,'broad_sector':r.broad_sector,'flagged_metrics':','.join(bad),'max_abs_z':max(abs(r[f'{f}_z']) for f in bad)})
    pd.DataFrame(out,columns=['company_id','ticker','broad_sector','flagged_metrics','max_abs_z']).to_csv(OUT/'outlier_report.csv',index=False)
    # portfolio stats for ten KPIs
    rows=[]
    for c in corr.columns:
        s=corr[c].dropna(); rows.append({'kpi':c,'P10':s.quantile(.10),'P25':s.quantile(.25),'P50':s.quantile(.50),'P75':s.quantile(.75),'P90':s.quantile(.90),'Mean':s.mean(),'Std':s.std()})
    pd.DataFrame(rows).to_csv(OUT/'portfolio_stats.csv',index=False)

if __name__=='__main__':
    mlabels,m,_=run_clustering(); profile_statistics(m,mlabels)
