import numpy as np
import plotly.graph_objects as go
import streamlit as st
from src.dashboard.utils.db import get_companies,get_latest_snapshot

st.title('Peer Comparison')
c=get_companies(); snap=get_latest_snapshot();
if c.empty or snap.empty: st.error('No data.'); st.stop()
group_col='peer_group' if 'peer_group' in c.columns else 'sector'; groups=sorted(c[group_col].dropna().unique()); group=st.selectbox('Peer group',groups); peers=c[c[group_col].eq(group)]
opts=[f'{r.company_name} ({r.ticker})' for _,r in peers.iterrows()]; selected=st.selectbox('Benchmark company',opts) if opts else None
if selected:
    ticker=selected.rsplit('(',1)[-1].rstrip(')'); base=snap[snap.ticker.eq(ticker)].iloc[0] if not snap[snap.ticker.eq(ticker)].empty else None
    metrics=['roe','roce','npm','opm','de','icr','revenue_cagr_5yr','pat_cagr_5yr']; labels=['ROE','ROCE','NPM','OPM','D/E','ICR','Revenue CAGR','PAT CAGR']
    if base is not None:
        vals=[]; avg=[]
        for m in metrics:
            vals.append(float(base[m]) if m in base and np.isfinite(base[m]) else 0); avg.append(float(snap[snap[group_col].eq(group)][m].mean()) if m in snap and snap[snap[group_col].eq(group)][m].notna().any() else 0)
        fig=go.Figure(); fig.add_trace(go.Scatterpolar(r=vals,theta=labels,fill='toself',name=ticker)); fig.add_trace(go.Scatterpolar(r=avg,theta=labels,fill='toself',name='Peer average')); fig.update_layout(polar=dict(radialaxis=dict(visible=True)),showlegend=True); st.plotly_chart(fig,use_container_width=True)
    st.dataframe(snap[snap.ticker.isin(peers.ticker)][[x for x in ['company_name','ticker','roe','roce','npm','opm','de','icr'] if x in snap.columns]].style.highlight_max(axis=0),use_container_width=True)
