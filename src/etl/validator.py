"""
validator.py — Day 03 deliverable
Implements DQ-01 .. DQ-16 against the loaded nifty100.db and writes
output/validation_failures.csv with a severity column (CRITICAL / WARNING).

CRITICAL rules must have zero failures before Day 05 (full load) proceeds.
"""
import csv
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

URL_RE = re.compile(r"^https?://[^\s]+$")

failures = []


def add_failure(rule_id, severity, table, description, offending_count, sample_ids=""):
    failures.append({
        "rule_id": rule_id,
        "severity": severity,
        "table": table,
        "description": description,
        "offending_rows": offending_count,
        "sample_ids": sample_ids,
    })


def sample(ids, n=5):
    ids = list(ids)
    return ", ".join(str(i) for i in ids[:n])


def run_all(conn):
    # ---------------- DQ-01: PK uniqueness (companies.company_id) ----------
    dupes = pd.read_sql(
        "SELECT company_id, COUNT(*) c FROM companies GROUP BY company_id HAVING c > 1", conn)
    add_failure("DQ-01", "CRITICAL", "companies",
                "company_id must be unique", len(dupes), sample(dupes["company_id"]))

    # ---------------- DQ-02: (company_id, year) PK on all yearly tables ----
    for tbl in ["profitandloss", "balancesheet", "cashflow", "financial_ratios"]:
        dupes = pd.read_sql(
            f"SELECT company_id, year, COUNT(*) c FROM {tbl} "
            f"GROUP BY company_id, year HAVING c > 1", conn)
        add_failure("DQ-02", "CRITICAL", tbl,
                    "(company_id, year) must be unique", len(dupes),
                    sample(dupes["company_id"]))

    # ---------------- DQ-03: FK integrity (all child tables -> companies) --
    fk_check = conn.execute("PRAGMA foreign_key_check;").fetchall()
    add_failure("DQ-03", "CRITICAL", "ALL",
                "Every FK must resolve to a valid companies.company_id",
                len(fk_check), sample([r[0] for r in fk_check]))

    # ---------------- DQ-04: Balance sheet balances within <1% ------------
    bs = pd.read_sql("SELECT company_id, year, total_assets, total_liabilities, "
                      "equity_capital FROM balancesheet", conn)
    bs["diff_pct"] = ((bs["total_assets"] - (bs["total_liabilities"] + bs["equity_capital"]))
                       .abs() / bs["total_assets"].replace(0, pd.NA)) * 100
    bad = bs[bs["diff_pct"] > 1.0]
    add_failure("DQ-04", "WARNING", "balancesheet",
                "Assets should equal Liabilities + Equity within 1%",
                len(bad), sample(bad["company_id"]))

    # ---------------- DQ-05: OPM cross-check (operating_profit/sales) ------
    pl = pd.read_sql("SELECT company_id, year, sales, operating_profit, opm_pct FROM profitandloss", conn)
    pl_valid = pl[pl["sales"] > 0].copy()
    pl_valid["calc_opm"] = (pl_valid["operating_profit"] / pl_valid["sales"]) * 100
    bad = pl_valid[(pl_valid["calc_opm"] - pl_valid["opm_pct"]).abs() > 2.0]
    add_failure("DQ-05", "WARNING", "profitandloss",
                "Reported OPM% should match operating_profit/sales within 2pp",
                len(bad), sample(bad["company_id"]))

    # ---------------- DQ-06: Positive sales ---------------------------------
    bad = pl[pl["sales"] <= 0]
    add_failure("DQ-06", "WARNING", "profitandloss",
                "Sales should be > 0", len(bad), sample(bad["company_id"]))

    # ---------------- DQ-07: Net cash flow = CFO + CFI + CFF ---------------
    cf = pd.read_sql("SELECT company_id, year, cash_from_operations, cash_from_investing, "
                      "cash_from_financing, net_cash_flow FROM cashflow", conn)
    cf["calc_net"] = cf["cash_from_operations"] + cf["cash_from_investing"] + cf["cash_from_financing"]
    bad = cf[(cf["calc_net"] - cf["net_cash_flow"]).abs() > 1.0]
    add_failure("DQ-07", "WARNING", "cashflow",
                "net_cash_flow should equal CFO+CFI+CFF (±1)", len(bad), sample(bad["company_id"]))

    # ---------------- DQ-08: Tax rate within plausible bounds (0-60%) ------
    bad = pl[(pl["company_id"].notna())]
    tax = pd.read_sql("SELECT company_id, year, tax_pct FROM profitandloss", conn)
    bad = tax[(tax["tax_pct"] < 0) | (tax["tax_pct"] > 60)]
    add_failure("DQ-08", "WARNING", "profitandloss",
                "tax_pct should be between 0% and 60%", len(bad), sample(bad["company_id"]))

    # ---------------- DQ-09: Dividend payout cap (<=100% flagged if over) --
    ratios = pd.read_sql("SELECT company_id, year, dividend_payout_pct FROM financial_ratios", conn)
    bad = ratios[ratios["dividend_payout_pct"] > 100]
    add_failure("DQ-09", "WARNING", "financial_ratios",
                "dividend_payout_pct should not exceed 100%", len(bad), sample(bad["company_id"]))

    # ---------------- DQ-10: URL format validity (documents.url) -----------
    docs = pd.read_sql("SELECT company_id, url FROM documents", conn)
    bad = docs[~docs["url"].astype(str).str.match(URL_RE)]
    add_failure("DQ-10", "WARNING", "documents",
                "Document URL must be a well-formed http(s) URL", len(bad), sample(bad["company_id"]))

    # ---------------- DQ-11: EPS sign sanity (net_profit>0 => eps>0) -------
    bad = pl[(pl["company_id"].notna())]
    epsdf = pd.read_sql("SELECT company_id, year, net_profit, eps FROM profitandloss", conn)
    bad = epsdf[(epsdf["net_profit"] > 0) & (epsdf["eps"] < 0)]
    add_failure("DQ-11", "WARNING", "profitandloss",
                "EPS sign should match net_profit sign", len(bad), sample(bad["company_id"]))

    # ---------------- DQ-12: BSE balance cross-check (assets vs BSE file) --
    try:
        bse = pd.read_excel(ROOT / "data" / "raw" / "12_bse_balance_check.xlsx")
        latest_bs = pd.read_sql(
            "SELECT company_id, MAX(year) as year, total_assets FROM balancesheet GROUP BY company_id", conn)
        merged = bse.merge(latest_bs, on="company_id", how="inner")
        merged["diff_pct"] = ((merged["total_assets"] - merged["bse_reported_assets"]).abs()
                               / merged["bse_reported_assets"].replace(0, pd.NA)) * 100
        bad = merged[merged["diff_pct"] > 5.0]
        add_failure("DQ-12", "WARNING", "balancesheet",
                    "Total assets should be within 5% of BSE-reported assets", len(bad),
                    sample(bad["company_id"]))
    except FileNotFoundError:
        add_failure("DQ-12", "WARNING", "balancesheet", "BSE cross-check source file missing", 0)

    # ---------------- DQ-13: Year coverage (>=5 years of P&L history) ------
    coverage = pd.read_sql(
        "SELECT company_id, COUNT(DISTINCT year) n FROM profitandloss GROUP BY company_id", conn)
    bad = coverage[coverage["n"] < 5]
    add_failure("DQ-13", "WARNING", "profitandloss",
                "Companies should have >= 5 years of P&L history", len(bad), sample(bad["company_id"]))

    # ---------------- DQ-14: Ticker format (no whitespace, uppercase) ------
    comp = pd.read_sql("SELECT company_id, ticker FROM companies", conn)
    bad = comp[comp["ticker"].astype(str).str.contains(r"\s") | (comp["ticker"] != comp["ticker"].str.upper())]
    add_failure("DQ-14", "WARNING", "companies",
                "Ticker must be uppercase with no embedded whitespace", len(bad), sample(bad["company_id"]))

    # ---------------- DQ-15: Non-negative stock prices/volume --------------
    prices = pd.read_sql("SELECT company_id, date, close_price, volume FROM stock_prices", conn)
    bad = prices[(prices["close_price"] <= 0) | (prices["volume"] < 0)]
    add_failure("DQ-15", "CRITICAL", "stock_prices",
                "close_price must be > 0 and volume must be >= 0", len(bad), sample(bad["company_id"]))

    # ---------------- DQ-16: Sector must exist in sectors lookup -----------
    comp_sectors = pd.read_sql("SELECT DISTINCT company_id, sector FROM companies", conn)
    valid_sectors = set(pd.read_sql("SELECT sector_name FROM sectors", conn)["sector_name"])
    bad = comp_sectors[~comp_sectors["sector"].isin(valid_sectors)]
    add_failure("DQ-16", "CRITICAL", "companies",
                "companies.sector must exist in sectors lookup table", len(bad),
                sample(bad["company_id"]))


def write_csv():
    path = OUTPUT_DIR / "validation_failures.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "rule_id", "severity", "table", "description", "offending_rows", "sample_ids"
        ])
        writer.writeheader()
        writer.writerows(failures)
    return path


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    run_all(conn)
    conn.close()

    path = write_csv()
    critical = [f for f in failures if f["severity"] == "CRITICAL" and f["offending_rows"] > 0]
    warnings = [f for f in failures if f["severity"] == "WARNING" and f["offending_rows"] > 0]

    print(f"Ran {len(failures)} DQ rules (DQ-01..DQ-16). Report: {path}")
    print(f"CRITICAL failures: {len(critical)}")
    for f in critical:
        print(f"  [{f['rule_id']}] {f['table']}: {f['offending_rows']} rows — {f['description']}")
    print(f"WARNING failures: {len(warnings)}")
    for f in warnings:
        print(f"  [{f['rule_id']}] {f['table']}: {f['offending_rows']} rows — {f['description']}")

    if critical:
        raise SystemExit("CRITICAL DQ failures must be resolved before proceeding to full load.")


if __name__ == "__main__":
    main()
