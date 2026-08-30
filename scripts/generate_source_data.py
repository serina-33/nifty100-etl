"""
generate_source_data.py
------------------------
Generates 12 synthetic source Excel files that stand in for the real
Nifty100 data extracts (7 core + 5 supplementary), so the ETL pipeline
(loader / normaliser / validator) has real .xlsx inputs to run against.

This is SYNTHETIC data for pipeline development/testing purposes only.
"""
import random
import string
import numpy as np
import pandas as pd
from pathlib import Path

random.seed(42)
np.random.seed(42)

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SECTORS = [
    "Banking", "IT Services", "FMCG", "Pharma", "Auto",
    "Energy", "Metals", "Infrastructure", "Telecom", "Consumer Durables"
]

N_COMPANIES = 92
YEARS = list(range(2011, 2025))  # 14 fiscal years -> gives ~1276-1312 rows for 92 cos

# ---------------------------------------------------------------
# 1. companies.xlsx  (core)
# ---------------------------------------------------------------
company_names = [f"Company_{i:03d} Ltd" for i in range(1, N_COMPANIES + 1)]
tickers = []
for i in range(N_COMPANIES):
    base = "".join(random.choices(string.ascii_uppercase, k=5))
    # introduce a few messy tickers on purpose to exercise normalize_ticker()
    if i % 17 == 0:
        base = f" {base.lower()}.ns "
    elif i % 23 == 0:
        base = f"{base}-EQ"
    tickers.append(base)

companies = pd.DataFrame({
    "company_id": range(1, N_COMPANIES + 1),
    "company_name": company_names,
    "ticker": tickers,
    "sector": [random.choice(SECTORS) for _ in range(N_COMPANIES)],
    "listing_date": pd.date_range("1995-01-01", "2015-01-01", periods=N_COMPANIES).strftime("%d-%b-%Y"),
    "isin": [f"INE{random.randint(100000,999999)}A01{random.randint(10,99)}" for _ in range(N_COMPANIES)],
})
companies.to_excel(RAW_DIR / "01_companies.xlsx", index=False)

# ---------------------------------------------------------------
# helper to build messy "year" columns to exercise normalize_year()
# ---------------------------------------------------------------
def messy_year(y):
    r = random.random()
    if r < 0.5:
        return y
    elif r < 0.65:
        return f"FY{y}"
    elif r < 0.8:
        return f"FY{y}-{str(y+1)[-2:]}"
    elif r < 0.9:
        return f"{y}-{str(y+1)[-2:]}"
    else:
        return f" {y} "

rows_pl, rows_bs, rows_cf, rows_prices = [], [], [], []

EXT_YEARS = list(range(2009, 2025))  # 16 possible fiscal years

for cid in range(1, N_COMPANIES + 1):
    # some companies only have partial year coverage (to exercise Day 06 review)
    # each statement independently has slightly different coverage, mirroring
    # how real annual-report extracts vary between P&L / BS / CF completeness
    is_thin = (cid % 12 == 0)
    n_pl = random.randint(2, 4) if is_thin else random.randint(14, 16)
    n_bs = random.randint(4, 6) if is_thin else random.randint(14, 16)
    n_cf = random.randint(2, 4) if is_thin else random.randint(12, 15)

    yrs_pl = EXT_YEARS[-n_pl:]
    yrs_bs = EXT_YEARS[-n_bs:]
    yrs_cf = EXT_YEARS[-n_cf:]

    for y in yrs_pl:
        sales = round(np.random.uniform(100, 50000), 2)
        opm = round(np.random.uniform(0.05, 0.35), 4)
        op_profit = round(sales * opm, 2)
        net_profit = round(op_profit * np.random.uniform(0.4, 0.9), 2)
        rows_pl.append({
            "company_id": cid, "year": messy_year(y),
            "sales": sales if random.random() > 0.01 else -abs(sales),  # inject rare negative sales
            "operating_profit": op_profit,
            "opm_pct": round(opm * 100, 2),
            "net_profit": net_profit,
            "eps": round(net_profit / random.randint(5, 50), 2) * random.choice([1, 1, 1, -1]),  # rare negative EPS
            "tax_pct": round(np.random.uniform(15, 35), 2),
        })

    for y in yrs_bs:
        total_assets = round(np.random.uniform(500, 80000), 2)
        liabilities = round(total_assets * np.random.uniform(0.4, 0.95), 2)
        equity = round(total_assets - liabilities, 2)
        # inject a small % of imbalanced balance sheets to trigger DQ-04
        if random.random() < 0.03:
            equity = round(equity * 1.15, 2)
        rows_bs.append({
            "company_id": cid, "year": messy_year(y),
            "total_assets": total_assets,
            "total_liabilities": liabilities,
            "equity_capital": equity,
            "reserves": round(equity * np.random.uniform(0.6, 0.9), 2),
            "borrowings": round(liabilities * np.random.uniform(0.2, 0.6), 2),
        })

    for y in yrs_cf:
        cfo = round(np.random.uniform(-500, 8000), 2)
        cfi = round(np.random.uniform(-4000, 500), 2)
        cff = round(np.random.uniform(-3000, 3000), 2)
        rows_cf.append({
            "company_id": cid, "year": messy_year(y),
            "cash_from_operations": cfo,
            "cash_from_investing": cfi,
            "cash_from_financing": cff,
            "net_cash_flow": round(cfo + cfi + cff, 2),
        })

    # stock prices ~60 monthly points per company => ~5520 for 92 cos
    dates = pd.date_range("2020-01-01", periods=60, freq="ME")
    price = np.random.uniform(50, 3000)
    for d in dates:
        price *= (1 + np.random.uniform(-0.08, 0.08))
        rows_prices.append({
            "company_id": cid, "date": d.strftime("%Y-%m-%d"),
            "close_price": round(price, 2),
            "volume": int(np.random.uniform(1e4, 5e6)),
        })

pd.DataFrame(rows_pl).to_excel(RAW_DIR / "02_profit_and_loss.xlsx", index=False)
pd.DataFrame(rows_bs).to_excel(RAW_DIR / "03_balance_sheet.xlsx", index=False)
pd.DataFrame(rows_cf).to_excel(RAW_DIR / "04_cash_flow.xlsx", index=False)
pd.DataFrame(rows_prices).to_excel(RAW_DIR / "05_stock_prices.xlsx", index=False)

# ---------------------------------------------------------------
# 6. analysis.xlsx (core) - narrative analyst notes
# ---------------------------------------------------------------
analysis = pd.DataFrame({
    "company_id": range(1, N_COMPANIES + 1),
    "analyst_rating": [random.choice(["Buy", "Hold", "Sell"]) for _ in range(N_COMPANIES)],
    "target_price": [round(np.random.uniform(100, 4000), 2) for _ in range(N_COMPANIES)],
    "summary": [f"Company_{i:03d} shows steady fundamentals with sector-typical margins." for i in range(1, N_COMPANIES+1)],
})
analysis.to_excel(RAW_DIR / "06_analysis.xlsx", index=False)

# ---------------------------------------------------------------
# 7. documents.xlsx (core) - annual report / filing links
# ---------------------------------------------------------------
documents = pd.DataFrame({
    "company_id": range(1, N_COMPANIES + 1),
    "doc_type": ["Annual Report"] * N_COMPANIES,
    "url": [f"https://www.bseindia.com/reports/company_{i:03d}_ar.pdf" if i % 11 != 0
            else f"not-a-valid-url-{i}" for i in range(1, N_COMPANIES + 1)],  # inject bad URLs for DQ
    "filed_date": pd.date_range("2024-01-01", periods=N_COMPANIES).strftime("%Y-%m-%d"),
})
documents.to_excel(RAW_DIR / "07_documents.xlsx", index=False)

# ---------------------------------------------------------------
# Supplementary files (5)
# ---------------------------------------------------------------
pros_cons = pd.DataFrame({
    "company_id": range(1, N_COMPANIES + 1),
    "pros": ["Strong brand; consistent ROE; healthy cash flow"] * N_COMPANIES,
    "cons": ["High valuation; sector cyclicality risk"] * N_COMPANIES,
})
pros_cons.to_excel(RAW_DIR / "08_pros_and_cons.xlsx", index=False)

sectors_df = pd.DataFrame({
    "sector_id": range(1, len(SECTORS) + 1),
    "sector_name": SECTORS,
    "sector_pe_avg": [round(np.random.uniform(12, 45), 2) for _ in SECTORS],
})
sectors_df.to_excel(RAW_DIR / "09_sectors.xlsx", index=False)

ratios_rows = []
for cid in range(1, N_COMPANIES + 1):
    for y in YEARS[-5:]:
        ratios_rows.append({
            "company_id": cid, "year": y,
            "pe_ratio": round(np.random.uniform(5, 60), 2),
            "pb_ratio": round(np.random.uniform(0.5, 15), 2),
            "roe_pct": round(np.random.uniform(2, 35), 2),
            "roce_pct": round(np.random.uniform(2, 40), 2),
            "debt_to_equity": round(np.random.uniform(0, 2.5), 2),
            "dividend_payout_pct": round(np.random.uniform(0, 130), 2),  # >100% on purpose for DQ
        })
pd.DataFrame(ratios_rows).to_excel(RAW_DIR / "10_financial_ratios.xlsx", index=False)

peer_rows = []
for cid in range(1, N_COMPANIES + 1):
    peers = random.sample([c for c in range(1, N_COMPANIES + 1) if c != cid], k=3)
    for p in peers:
        peer_rows.append({"company_id": cid, "peer_company_id": p})
pd.DataFrame(peer_rows).to_excel(RAW_DIR / "11_peer_groups.xlsx", index=False)

# BSE cross-check file (balance verification source, supplementary)
bse_check = pd.DataFrame({
    "company_id": range(1, N_COMPANIES + 1),
    "year": [YEARS[-1]] * N_COMPANIES,
    "bse_reported_assets": [round(np.random.uniform(500, 80000), 2) for _ in range(N_COMPANIES)],
})
bse_check.to_excel(RAW_DIR / "12_bse_balance_check.xlsx", index=False)

print("Generated 12 source files in", RAW_DIR)
for f in sorted(RAW_DIR.glob("*.xlsx")):
    print(" -", f.name)
