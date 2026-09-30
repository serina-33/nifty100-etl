import pandas as pd
import plotly.express as px
import streamlit as st
from src.dashboard.utils.db import get_companies,get_cf,get_pl

st.title('Capital Allocation Patterns')
rows=[]
for _,c in get_companies().iterrows():
    cf=get_cf(c.ticker); pl=get_pl(c.ticker)
    if cf.empty: continue
    z=cf.sort_values('year').iloc[-1]; pat=pl.sort_values('year').iloc[-1]['net_profit'] if not pl.empty else None; cfo=z.cash_from_operations or 0; cfi=z.cash_from_investing or 0; cff=z.cash_from_financing or 0
    ratio=(cfo/pat) if pat not in (None,0) else None
    from src.analytics.cashflow_kpis import capital_allocation_pattern
    rows.append({'company_name':c.company_name,'ticker':c.ticker,'pattern':capital_allocation_pattern(cfo,cfi,cff,ratio)})
df=pd.DataFrame(rows); 
if df.empty: st.info('No cash-flow data.'); st.stop()
counts=df.pattern.value_counts().reset_index(); counts.columns=['pattern','count']; st.plotly_chart(px.treemap(counts,path=['pattern'],values='count',title='Capital allocation patterns'),use_container_width=True)
pat=st.selectbox('Select pattern',sorted(df.pattern.unique())); st.dataframe(df[df.pattern.eq(pat)],hide_index=True,use_container_width=True)
