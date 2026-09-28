"""
patch_companies_sprint2.py
---------------------------
Sprint 2 (Day 13) needs two things Sprint 1 didn't produce:

1. A `broad_sector` classification, where Banking + a handful of NBFC/insurance-like
   companies from adjacent sectors roll up into "Financials" (19 companies total,
   mirroring how ~19-20 of the real Nifty100 constituents are financial-sector firms
   even though "Banking" alone is a narrower label).
2. A supplementary source file with PRE-COMPUTED roce_percentage / roe_percentage
   values (as if pulled from a third-party data vendor), including a few
   intentionally anomalous values -- e.g. one company's roe_percentage_source
   is deliberately nonsensical (mirrors the sprint note "TCS shows 0.52") -- so
   Day 13's cross-check-and-log-anomalies step has real anomalies to find.

This does NOT modify the original Sprint 1 `01_companies.xlsx` or the `companies`
table's core columns -- it only ADDS an additive `broad_sector` column to the
companies table (safe, non-breaking) and writes a new supplementary file
`data/raw/13_precomputed_ratios.xlsx` + `company_precomputed_ratios` table.
"""
import random
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(7)
np.random.seed(7)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "nifty100.db"
RAW_DIR = ROOT / "data" / "raw"

TARGET_FINANCIALS_COUNT = 19


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    companies = pd.read_sql("SELECT company_id, sector FROM companies", conn)

    banking_ids = companies.loc[companies["sector"] == "Banking", "company_id"].tolist()
    non_banking_ids = companies.loc[companies["sector"] != "Banking", "company_id"].tolist()

    extra_needed = max(0, TARGET_FINANCIALS_COUNT - len(banking_ids))
    extra_financials = random.sample(non_banking_ids, k=min(extra_needed, len(non_banking_ids)))
    financials_ids = set(banking_ids) | set(extra_financials)

    companies["broad_sector"] = companies["company_id"].apply(
        lambda cid: "Financials" if cid in financials_ids else "Non-Financials"
    )

    # --- 1. Add broad_sector column to companies table (additive, non-breaking) ---
    cols = [r[1] for r in conn.execute("PRAGMA table_info(companies)").fetchall()]
    if "broad_sector" not in cols:
        conn.execute("ALTER TABLE companies ADD COLUMN broad_sector TEXT;")
    for _, row in companies.iterrows():
        conn.execute("UPDATE companies SET broad_sector = ? WHERE company_id = ?",
                     (row["broad_sector"], int(row["company_id"])))
    conn.commit()

    # --- 2. Build supplementary pre-computed ratios source file ---
    # Use the latest year of computed ROE/ROCE from financial_ratios (if present)
    # as a baseline, then add vendor-style noise + a few deliberate anomalies.
    try:
        latest_ratios = pd.read_sql(
            "SELECT fr.company_id, fr.return_on_equity_pct AS roe_pct, "
            "fr.return_on_capital_employed_pct AS roce_pct "
            "FROM financial_ratios fr "
            "INNER JOIN (SELECT company_id, MAX(year) AS max_year FROM financial_ratios GROUP BY company_id) latest "
            "ON fr.company_id = latest.company_id AND fr.year = latest.max_year",
            conn)
    except Exception:
        latest_ratios = pd.DataFrame(columns=["company_id", "roe_pct", "roce_pct"])

    baseline = companies.merge(latest_ratios, on="company_id", how="left")
    baseline["roe_pct"] = baseline["roe_pct"].fillna(pd.Series(np.random.uniform(5, 25, len(baseline)), index=baseline.index))
    baseline["roce_pct"] = baseline["roce_pct"].fillna(pd.Series(np.random.uniform(5, 25, len(baseline)), index=baseline.index))

    rows = []
    anomaly_ids = random.sample(list(companies["company_id"]), k=5)
    for _, r in baseline.iterrows():
        cid = int(r["company_id"])
        roe_source = round(r["roe_pct"] * np.random.uniform(0.95, 1.05), 2)
        roce_source = round(r["roce_pct"] * np.random.uniform(0.95, 1.05), 2)
        if cid in anomaly_ids:
            # deliberate vendor-data glitch, e.g. decimal/unit error (0.52 instead of 52.0)
            roe_source = round(roe_source / 100, 4)
        rows.append({
            "company_id": cid,
            "roce_percentage_source": roce_source,
            "roe_percentage_source": roe_source,
        })

    precomputed = pd.DataFrame(rows)
    precomputed.to_excel(RAW_DIR / "13_precomputed_ratios.xlsx", index=False)

    conn.execute("DROP TABLE IF EXISTS company_precomputed_ratios;")
    conn.execute("""
        CREATE TABLE company_precomputed_ratios (
            company_id INTEGER PRIMARY KEY,
            roce_percentage_source REAL,
            roe_percentage_source REAL,
            FOREIGN KEY (company_id) REFERENCES companies(company_id)
        );
    """)
    precomputed.to_sql("company_precomputed_ratios", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()

    print(f"broad_sector added: {len(financials_ids)} companies classified as Financials")
    print(f"Wrote {RAW_DIR / '13_precomputed_ratios.xlsx'} and company_precomputed_ratios table")
    print(f"Deliberate anomaly company_ids planted: {sorted(anomaly_ids)}")


if __name__ == "__main__":
    main()
