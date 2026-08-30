"""
populate_ratios.py — Sprint 2, Day 12 deliverable
Runs the full ratio engine (ratios.py + cagr.py + cashflow_kpis.py) for all
92 companies across every available company-year, and writes the results
into a rebuilt `financial_ratios` table with 17 KPI/flag columns.

Also produces:
  - output/capital_allocation.csv   (Day 11 deliverable, 8-pattern label per company-year)
  - a composite_quality_score column combining ROE, D/E, and CFO quality

Row-count target (Day 12 exit criterion): >= 1,100 rows.
"""
import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ratios import (  # noqa: E402
    net_profit_margin, operating_profit_margin, opm_cross_check,
    return_on_equity, return_on_capital_employed, return_on_assets,
    debt_to_equity, high_leverage_flag, interest_coverage_ratio,
    icr_label, icr_warning_flag, net_debt, asset_turnover,
)
from cagr import compute_windowed_cagr  # noqa: E402
from cashflow_kpis import (  # noqa: E402
    free_cash_flow, cfo_quality_score, capex_intensity,
    fcf_conversion_rate, capital_allocation_pattern,
)

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
RAW_DIVIDEND_FILE = ROOT / "data" / "raw" / "10_financial_ratios.xlsx"

NEW_SCHEMA = """
DROP TABLE IF EXISTS financial_ratios;
CREATE TABLE financial_ratios (
    company_id                   INTEGER NOT NULL,
    year                         INTEGER NOT NULL,
    net_profit_margin_pct        REAL,
    operating_profit_margin_pct  REAL,
    opm_mismatch_flag            INTEGER,
    return_on_equity_pct         REAL,
    return_on_capital_employed_pct REAL,
    return_on_assets_pct         REAL,
    debt_to_equity               REAL,
    high_leverage_flag           INTEGER,
    interest_coverage            REAL,
    icr_label                    TEXT,
    icr_warning_flag             INTEGER,
    net_debt_cr                  REAL,
    asset_turnover               REAL,
    free_cash_flow_cr            REAL,
    capex_cr                     REAL,
    capex_intensity_label        TEXT,
    fcf_conversion_rate_pct      REAL,
    earnings_per_share           REAL,
    book_value_per_share         REAL,
    dividend_payout_ratio_pct    REAL,
    total_debt_cr                REAL,
    cash_from_operations_cr      REAL,
    revenue_cagr_5yr             REAL,
    revenue_cagr_5yr_flag        TEXT,
    pat_cagr_5yr                 REAL,
    pat_cagr_5yr_flag            TEXT,
    eps_cagr_5yr                 REAL,
    eps_cagr_5yr_flag            TEXT,
    cfo_quality_score            REAL,
    cfo_quality_label            TEXT,
    composite_quality_score      REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);
"""


def fetch_company_year_data(conn):
    """
    Returns {company_id: {"is_financials": bool, "years": {year: {...merged fields...}}}}
    by outer-joining P&L, balance sheet, and cash flow on (company_id, year), so
    a company-year with e.g. P&L but no matching cash flow row still appears
    (with None for the missing cash flow fields) rather than being dropped.
    """
    companies = conn.execute(
        "SELECT company_id, COALESCE(broad_sector, 'Non-Financials') FROM companies").fetchall()
    is_financials = {cid: (bs == "Financials") for cid, bs in companies}

    pl = conn.execute(
        "SELECT company_id, year, sales, operating_profit, opm_pct, net_profit, eps, tax_pct "
        "FROM profitandloss").fetchall()
    bs = conn.execute(
        "SELECT company_id, year, total_assets, total_liabilities, equity_capital, reserves, borrowings "
        "FROM balancesheet").fetchall()
    cf = conn.execute(
        "SELECT company_id, year, cash_from_operations, cash_from_investing, cash_from_financing, net_cash_flow "
        "FROM cashflow").fetchall()

    data = {}

    def ensure(cid, year):
        data.setdefault(cid, {})
        data[cid].setdefault(year, {})
        return data[cid][year]

    for cid, year, sales, op_profit, opm_pct, net_profit, eps, tax_pct in pl:
        row = ensure(cid, year)
        row.update(sales=sales, operating_profit=op_profit, opm_pct=opm_pct,
                   net_profit=net_profit, eps=eps, tax_pct=tax_pct)

    for cid, year, total_assets, total_liab, equity, reserves, borrowings in bs:
        row = ensure(cid, year)
        row.update(total_assets=total_assets, total_liabilities=total_liab,
                   equity_capital=equity, reserves=reserves, borrowings=borrowings)

    for cid, year, cfo, cfi, cff, net_cf in cf:
        row = ensure(cid, year)
        row.update(cash_from_operations=cfo, cash_from_investing=cfi,
                   cash_from_financing=cff, net_cash_flow=net_cf)

    return data, is_financials


def build_yearly_series(years_dict, field):
    return {y: v.get(field) for y, v in years_dict.items() if v.get(field) is not None}


def compute_row(cid, year, row, all_years_for_company, is_fin):
    sales = row.get("sales")
    op_profit = row.get("operating_profit")
    net_profit = row.get("net_profit")
    eps = row.get("eps")
    total_assets = row.get("total_assets")
    equity = row.get("equity_capital")
    reserves = row.get("reserves")
    borrowings = row.get("borrowings")
    cfo = row.get("cash_from_operations")
    cfi = row.get("cash_from_investing")
    cff = row.get("cash_from_financing")

    # EBIT approximated as operating_profit (no separate D&A/interest split in source data)
    ebit = op_profit
    other_income = 0  # not separately captured in source data; treated as 0
    interest = None
    if borrowings is not None and borrowings > 0:
        # approximate interest expense as a fraction of borrowings when not directly available
        interest = round(borrowings * 0.08, 4)

    npm = net_profit_margin(net_profit, sales) if net_profit is not None and sales is not None else None
    opm_calc = operating_profit_margin(op_profit, sales) if op_profit is not None and sales is not None else None
    opm_check = opm_cross_check(opm_calc, row.get("opm_pct"))

    roe = return_on_equity(net_profit, equity, reserves) if net_profit is not None else None
    roce = return_on_capital_employed(ebit, equity, reserves, borrowings) if ebit is not None else None
    roa = return_on_assets(net_profit, total_assets) if net_profit is not None and total_assets is not None else None

    de = debt_to_equity(borrowings, equity, reserves) if borrowings is not None else None
    lev_flag = high_leverage_flag(de, is_fin)
    icr = interest_coverage_ratio(op_profit, other_income, interest) if op_profit is not None else None
    label = icr_label(icr) if interest is not None else None
    icr_warn = icr_warning_flag(icr)
    ndebt = net_debt(borrowings, 0) if borrowings is not None else None
    at = asset_turnover(sales, total_assets) if sales is not None and total_assets is not None else None

    fcf = free_cash_flow(cfo, cfi) if cfo is not None or cfi is not None else None
    capex_val, capex_label = capex_intensity(cfi, sales) if cfi is not None and sales is not None else (None, None)
    fcf_conv = fcf_conversion_rate(fcf, op_profit) if fcf is not None and op_profit is not None else None

    book_value_per_share = None
    if equity is not None and reserves is not None and eps not in (None, 0) and net_profit not in (None, 0):
        # approximate shares outstanding from EPS and net profit, then derive BVPS
        try:
            shares = net_profit / eps
            if shares:
                book_value_per_share = round((equity + reserves) / shares, 4)
        except ZeroDivisionError:
            book_value_per_share = None

    dividend_payout_pct = None
    dividend_lookup = DIVIDEND_LOOKUP.get((cid, year))
    if dividend_lookup is not None:
        dividend_payout_pct = dividend_lookup

    # ---- CAGR (5-year windows) ----
    revenue_series = build_yearly_series(all_years_for_company, "sales")
    pat_series = build_yearly_series(all_years_for_company, "net_profit")
    eps_series = build_yearly_series(all_years_for_company, "eps")

    rev_cagr, rev_flag = compute_windowed_cagr(revenue_series, year, 5)
    pat_cagr, pat_flag = compute_windowed_cagr(pat_series, year, 5)
    eps_cagr, eps_flag = compute_windowed_cagr(eps_series, year, 5)

    # ---- CFO quality score (trailing up to 5 years) ----
    years_sorted = sorted(y for y in all_years_for_company if y <= year)[-5:]
    cfo_trail = [all_years_for_company[y].get("cash_from_operations") for y in years_sorted]
    pat_trail = [all_years_for_company[y].get("net_profit") for y in years_sorted]
    cfo_q_ratio, cfo_q_label = cfo_quality_score(cfo_trail, pat_trail)

    pattern_label = capital_allocation_pattern(cfo, cfi, cff, cfo_pat_ratio=cfo_q_ratio) \
        if cfo is not None and cfi is not None and cff is not None else None

    # ---- Composite quality score: simple weighted blend, 0-100 scale ----
    components = []
    if roe is not None:
        components.append(min(max(roe, -50), 50) + 50)  # normalize roughly into 0-100
    if de is not None:
        components.append(max(0, 100 - de * 20))
    if cfo_q_ratio is not None:
        components.append(min(cfo_q_ratio, 2) * 50)
    composite = round(sum(components) / len(components), 2) if components else None

    return {
        "company_id": cid, "year": year,
        "net_profit_margin_pct": npm,
        "operating_profit_margin_pct": opm_calc,
        "opm_mismatch_flag": int(opm_check["mismatch"]),
        "return_on_equity_pct": roe,
        "return_on_capital_employed_pct": roce,
        "return_on_assets_pct": roa,
        "debt_to_equity": de,
        "high_leverage_flag": int(lev_flag),
        "interest_coverage": icr,
        "icr_label": label,
        "icr_warning_flag": int(icr_warn),
        "net_debt_cr": ndebt,
        "asset_turnover": at,
        "free_cash_flow_cr": fcf,
        "capex_cr": cfi,
        "capex_intensity_label": capex_label,
        "fcf_conversion_rate_pct": fcf_conv,
        "earnings_per_share": eps,
        "book_value_per_share": book_value_per_share,
        "dividend_payout_ratio_pct": dividend_payout_pct,
        "total_debt_cr": borrowings,
        "cash_from_operations_cr": cfo,
        "revenue_cagr_5yr": rev_cagr, "revenue_cagr_5yr_flag": rev_flag,
        "pat_cagr_5yr": pat_cagr, "pat_cagr_5yr_flag": pat_flag,
        "eps_cagr_5yr": eps_cagr, "eps_cagr_5yr_flag": eps_flag,
        "cfo_quality_score": cfo_q_ratio,
        "cfo_quality_label": cfo_q_label,
        "composite_quality_score": composite,
        "_pattern_label": pattern_label,  # written to capital_allocation.csv, not the DB table
        "_cfo_sign": ("+" if (cfo or 0) >= 0 else "-") if cfo is not None else None,
        "_cfi_sign": ("+" if (cfi or 0) >= 0 else "-") if cfi is not None else None,
        "_cff_sign": ("+" if (cff or 0) >= 0 else "-") if cff is not None else None,
    }


def load_dividend_lookup():
    """
    Loads the Sprint 1 supplementary 10_financial_ratios.xlsx source, which
    carries a vendor-reported dividend_payout_pct for the last 5 years per
    company -- used directly here rather than re-derived, since dividend
    declarations aren't reconstructable from P&L/BS/CF alone.
    """
    if not RAW_DIVIDEND_FILE.exists():
        return {}
    df = pd.read_excel(RAW_DIVIDEND_FILE)
    return {(int(r.company_id), int(r.year)): r.dividend_payout_pct for r in df.itertuples()}


DIVIDEND_LOOKUP = load_dividend_lookup()


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(NEW_SCHEMA)

    data, is_financials_map = fetch_company_year_data(conn)

    db_columns = [
        "company_id", "year", "net_profit_margin_pct", "operating_profit_margin_pct",
        "opm_mismatch_flag", "return_on_equity_pct", "return_on_capital_employed_pct",
        "return_on_assets_pct", "debt_to_equity", "high_leverage_flag", "interest_coverage",
        "icr_label", "icr_warning_flag", "net_debt_cr", "asset_turnover", "free_cash_flow_cr",
        "capex_cr", "capex_intensity_label", "fcf_conversion_rate_pct", "earnings_per_share",
        "book_value_per_share", "dividend_payout_ratio_pct", "total_debt_cr",
        "cash_from_operations_cr", "revenue_cagr_5yr", "revenue_cagr_5yr_flag",
        "pat_cagr_5yr", "pat_cagr_5yr_flag", "eps_cagr_5yr", "eps_cagr_5yr_flag",
        "cfo_quality_score", "cfo_quality_label", "composite_quality_score",
    ]
    placeholders = ", ".join(["?"] * len(db_columns))
    insert_sql = f"INSERT INTO financial_ratios ({', '.join(db_columns)}) VALUES ({placeholders})"

    capital_allocation_rows = []
    inserted = 0

    for cid, years_dict in data.items():
        is_fin = is_financials_map.get(cid, False)
        for year, row in years_dict.items():
            computed = compute_row(cid, year, row, years_dict, is_fin)
            conn.execute(insert_sql, tuple(computed[c] for c in db_columns))
            inserted += 1

            if computed["_pattern_label"] is not None:
                capital_allocation_rows.append({
                    "company_id": cid, "year": year,
                    "cfo_sign": computed["_cfo_sign"],
                    "cfi_sign": computed["_cfi_sign"],
                    "cff_sign": computed["_cff_sign"],
                    "pattern_label": computed["_pattern_label"],
                })

    conn.commit()

    # ---- Write output/capital_allocation.csv ----
    ca_path = OUTPUT_DIR / "capital_allocation.csv"
    with open(ca_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"])
        writer.writeheader()
        writer.writerows(capital_allocation_rows)

    total_rows = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    print(f"Inserted {inserted} rows into financial_ratios (target: >= 1100)")
    print(f"financial_ratios row count check: {total_rows}")
    print(f"Wrote {len(capital_allocation_rows)} rows to {ca_path}")

    null_only_cols = []
    for col in db_columns[2:]:
        non_null = conn.execute(f"SELECT COUNT(*) FROM financial_ratios WHERE {col} IS NOT NULL").fetchone()[0]
        if non_null == 0:
            null_only_cols.append(col)
    if null_only_cols:
        print("WARNING - columns with zero non-null values:", null_only_cols)
    else:
        print("All KPI columns have at least some populated values (no null-only columns).")

    conn.close()

    if total_rows < 1100:
        raise SystemExit(f"Row count {total_rows} is below the 1,100 exit-criterion threshold.")


if __name__ == "__main__":
    main()
