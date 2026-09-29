import pandas as pd
import plotly.express as px
import streamlit as st
from src.dashboard.utils.db import get_companies,get_latest_snapshot

st.title('Sector Analytics'); d=get_latest_snapshot(); c=get_companies();
sector=st.selectbox('Sector',sorted(c.sector.dropna().unique())); x=d[d.sector.eq(sector)].copy()
for q in ['sales','market_cap_cr','roe','roce']: x[q]=pd.to_numeric(x[q],errors='coerce') if q in x else pd.NA
if not x.empty:
    st.plotly_chart(px.scatter(x,x='sales',y='roe',size='market_cap_cr',color='sub_sector' if 'sub_sector' in x else None,hover_name='company_name',title=f'{sector}: Revenue vs ROE'),use_container_width=True)
med=x[['roe','roce','opm','de','revenue_cagr_5yr']].median().reset_index(name='median').rename(columns={'index':'metric'}); st.plotly_chart(px.bar(med,x='metric',y='median',title='Sector median KPIs'),use_container_width=True)
