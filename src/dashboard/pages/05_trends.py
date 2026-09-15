import plotly.graph_objects as go
import streamlit as st
from src.dashboard.utils.db import get_companies,get_ratios

st.title('Financial Trends')
c=get_companies(); labels={f'{r.company_name} ({r.ticker})':r.ticker for _,r in c.iterrows()}; choice=st.selectbox('Company',list(labels)); ticker=labels[choice]; r=get_ratios(ticker)
metrics=[m for m in ['roe_pct','roce_pct','opm_pct','debt_to_equity','pe_ratio','pb_ratio','dividend_payout_pct'] if m in r.columns]; chosen=st.multiselect('Choose up to 3 metrics',metrics,default=metrics[:2],max_selections=3)
fig=go.Figure()
for m in chosen:
    y=r[m].astype(float); fig.add_trace(go.Scatter(x=r.year,y=y,mode='lines+markers',name=m))
fig.update_layout(title='10-year trend',xaxis_title='Year',yaxis_title='Value'); st.plotly_chart(fig,use_container_width=True)
if not r.empty: st.dataframe(r[['year']+chosen],hide_index=True,use_container_width=True)
