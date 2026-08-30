"""
loader.py — Day 04/05 deliverable
Loads all 12 source Excel files into nifty100.db following the load
order: companies -> sectors -> P&L -> BS -> CF -> analysis -> documents
       -> pros_and_cons -> stock_prices -> financial_ratios -> peer_groups

Produces output/load_audit.csv with per-table row counts & rejections,
and enforces PRAGMA foreign_keys = ON throughout.
"""
import sqlite3
import sys
import csv
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normaliser import normalize_year, normalize_ticker  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
SCHEMA_PATH = ROOT / "db" / "schema.sql"

audit_rows = []


def log_audit(table, source_file, rows_read, rows_loaded, rows_rejected, notes=""):
    audit_rows.append({
        "table": table,
        "source_file": source_file,
        "rows_read": rows_read,
        "rows_loaded": rows_loaded,
        "rows_rejected": rows_rejected,
        "notes": notes,
    })


def build_schema(conn):
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


def load_companies(conn):
    df = pd.read_excel(RAW_DIR / "01_companies.xlsx")
    df["ticker"] = df["ticker"].apply(normalize_ticker)
    before = len(df)
    df = df.dropna(subset=["company_id", "ticker"])
    df.to_sql("companies", conn, if_exists="append", index=False)
    log_audit("companies", "01_companies.xlsx", before, len(df), before - len(df))


def load_sectors(conn):
    df = pd.read_excel(RAW_DIR / "09_sectors.xlsx")
    before = len(df)
    df.to_sql("sectors", conn, if_exists="append", index=False)
    log_audit("sectors", "09_sectors.xlsx", before, len(df), 0)


def _load_yearly_table(conn, table, filename, columns):
    df = pd.read_excel(RAW_DIR / filename)
    before = len(df)
    df["year"] = df["year"].apply(normalize_year)
    valid_ids = pd.read_sql("SELECT company_id FROM companies", conn)["company_id"].tolist()

    rejected = df[df["year"].isna() | ~df["company_id"].isin(valid_ids)]
    df = df[df["year"].notna() & df["company_id"].isin(valid_ids)]
    df = df.drop_duplicates(subset=["company_id", "year"], keep="first")
    df = df[columns]
    df.to_sql(table, conn, if_exists="append", index=False)
    log_audit(table, filename, before, len(df), len(rejected),
              notes="dropped bad year / orphan FK / dup PK" if len(rejected) else "")


def load_pl(conn):
    _load_yearly_table(conn, "profitandloss", "02_profit_and_loss.xlsx",
                        ["company_id", "year", "sales", "operating_profit",
                         "opm_pct", "net_profit", "eps", "tax_pct"])


def load_bs(conn):
    _load_yearly_table(conn, "balancesheet", "03_balance_sheet.xlsx",
                        ["company_id", "year", "total_assets", "total_liabilities",
                         "equity_capital", "reserves", "borrowings"])


def load_cf(conn):
    _load_yearly_table(conn, "cashflow", "04_cash_flow.xlsx",
                        ["company_id", "year", "cash_from_operations",
                         "cash_from_investing", "cash_from_financing", "net_cash_flow"])


def load_analysis(conn):
    df = pd.read_excel(RAW_DIR / "06_analysis.xlsx")
    before = len(df)
    df.to_sql("analysis", conn, if_exists="append", index=False)
    log_audit("analysis", "06_analysis.xlsx", before, len(df), 0)


def load_documents(conn):
    df = pd.read_excel(RAW_DIR / "07_documents.xlsx")
    before = len(df)
    df = df[["company_id", "doc_type", "url", "filed_date"]]
    df.to_sql("documents", conn, if_exists="append", index=False)
    log_audit("documents", "07_documents.xlsx", before, len(df), 0)


def load_pros_cons(conn):
    df = pd.read_excel(RAW_DIR / "08_pros_and_cons.xlsx")
    before = len(df)
    df.to_sql("prosandcons", conn, if_exists="append", index=False)
    log_audit("prosandcons", "08_pros_and_cons.xlsx", before, len(df), 0)


def load_prices(conn):
    df = pd.read_excel(RAW_DIR / "05_stock_prices.xlsx")
    before = len(df)
    df = df.drop_duplicates(subset=["company_id", "date"], keep="first")
    df.to_sql("stock_prices", conn, if_exists="append", index=False)
    log_audit("stock_prices", "05_stock_prices.xlsx", before, len(df), before - len(df))


def load_ratios(conn):
    _load_yearly_table(conn, "financial_ratios", "10_financial_ratios.xlsx",
                        ["company_id", "year", "pe_ratio", "pb_ratio", "roe_pct",
                         "roce_pct", "debt_to_equity", "dividend_payout_pct"])


def load_peer_groups(conn):
    df = pd.read_excel(RAW_DIR / "11_peer_groups.xlsx")
    before = len(df)
    valid_ids = set(pd.read_sql("SELECT company_id FROM companies", conn)["company_id"])
    df = df[df["company_id"].isin(valid_ids) & df["peer_company_id"].isin(valid_ids)]
    df = df.drop_duplicates(subset=["company_id", "peer_company_id"])
    df.to_sql("peer_groups", conn, if_exists="append", index=False)
    log_audit("peer_groups", "11_peer_groups.xlsx", before, len(df), before - len(df))


def write_audit_csv():
    path = OUTPUT_DIR / "load_audit.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "table", "source_file", "rows_read", "rows_loaded", "rows_rejected", "notes"
        ])
        writer.writeheader()
        writer.writerows(audit_rows)
    return path


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    build_schema(conn)

    load_companies(conn)
    load_sectors(conn)
    load_pl(conn)
    load_bs(conn)
    load_cf(conn)
    load_analysis(conn)
    load_documents(conn)
    load_pros_cons(conn)
    load_prices(conn)
    load_ratios(conn)
    load_peer_groups(conn)

    conn.commit()

    fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    conn.close()

    audit_path = write_audit_csv()

    print(f"Loaded database at: {DB_PATH}")
    print(f"Load audit written to: {audit_path}")
    print(f"PRAGMA foreign_key_check violations: {len(fk_violations)}")
    for row in audit_rows:
        print(f"  {row['table']:<18} read={row['rows_read']:<6} "
              f"loaded={row['rows_loaded']:<6} rejected={row['rows_rejected']}")

    if fk_violations:
        print("FK VIOLATIONS FOUND:", fk_violations)
        sys.exit(1)


if __name__ == "__main__":
    main()
