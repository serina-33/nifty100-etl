import pandas as pd
from src.analytics.peer import compute_percentiles

def test_percent_rank_low_high():
    df=pd.DataFrame({
        "company_id":[1,2,3],"year":[2024,2024,2024],
        "return_on_equity_pct":[10,20,30],"return_on_capital_employed_pct":[5,10,15],
        "net_profit_margin_pct":[5,10,15],"debt_to_equity":[3,2,1],
        "free_cash_flow_cr":[10,20,30],"pat_cagr_5yr":[5,10,15],
        "revenue_cagr_5yr":[5,10,15],"eps_cagr_5yr":[5,10,15],
        "interest_coverage":[2,4,6],"asset_turnover":[.5,1,1.5]})
    a=pd.DataFrame({"company_id":[1,2,3],"peer_group_name":["IT Services"]*3,"is_benchmark":[False]*3})
    p=compute_percentiles(df,a)
    roe=p[p.metric=="roe"].sort_values("company_id")
    assert list(roe.percentile_rank)==[0,.5,1]
    de=p[p.metric=="debt_to_equity"].sort_values("company_id")
    assert list(de.percentile_rank)==[0, .5, 1]

def test_no_assignments_is_empty():
    df=pd.DataFrame({"company_id":[1],"year":[2024],"return_on_equity_pct":[20]})
    a=pd.DataFrame(columns=["company_id","peer_group_name"])
    assert compute_percentiles(df,a).empty
