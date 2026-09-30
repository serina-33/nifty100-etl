"""
spot_check.py — Sprint 2, Day 12/14 deliverable
Manual spot-check: for 3 companies, independently recomputes ROE and the
5-year Revenue CAGR from the raw P&L/balance-sheet tables (as if doing it
by hand in a spreadsheet) and compares to what's stored in financial_ratios.
Exit criterion: difference must be < 0.1%.
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"

SPOT_CHECK_COMPANY_IDS = [1, 25, 60]


def independent_roe(conn, company_id, year):
    row = conn.execute(
        "SELECT net_profit FROM profitandloss WHERE company_id=? AND year=?", (company_id, year)).fetchone()
    bs = conn.execute(
        "SELECT equity_capital, reserves FROM balancesheet WHERE company_id=? AND year=?",
        (company_id, year)).fetchone()
    if not row or not bs:
        return None
    net_profit = row[0]
    denom = (bs[0] or 0) + (bs[1] or 0)
    if denom <= 0:
        return None
    return round((net_profit / denom) * 100, 4)


def independent_revenue_cagr_5yr(conn, company_id, year):
    start_year = year - 5
    start = conn.execute(
        "SELECT sales FROM profitandloss WHERE company_id=? AND year=?", (company_id, start_year)).fetchone()
    end = conn.execute(
        "SELECT sales FROM profitandloss WHERE company_id=? AND year=?", (company_id, year)).fetchone()
    if not start or not end or start[0] is None or end[0] is None or start[0] <= 0 or end[0] <= 0:
        return None
    return round(((end[0] / start[0]) ** (1 / 5) - 1) * 100, 4)


def main():
    conn = sqlite3.connect(DB_PATH)
    print(f"{'company_id':>10} | {'metric':<18} | {'db_value':>12} | {'manual_value':>12} | {'diff_pct':>10} | status")
    print("-" * 90)

    all_ok = True
    for cid in SPOT_CHECK_COMPANY_IDS:
        latest_year = conn.execute(
            "SELECT MAX(year) FROM financial_ratios WHERE company_id=?", (cid,)).fetchone()[0]
        if latest_year is None:
            print(f"{cid:>10} | no financial_ratios row found -- skipping")
            continue

        db_roe, db_rev_cagr = conn.execute(
            "SELECT return_on_equity_pct, revenue_cagr_5yr FROM financial_ratios "
            "WHERE company_id=? AND year=?", (cid, latest_year)).fetchone()

        manual_roe = independent_roe(conn, cid, latest_year)
        manual_cagr = independent_revenue_cagr_5yr(conn, cid, latest_year)

        for metric, db_val, manual_val in [
            ("ROE %", db_roe, manual_roe),
            ("Revenue CAGR 5yr %", db_rev_cagr, manual_cagr),
        ]:
            if db_val is None or manual_val is None:
                status = "N/A (insufficient data)"
                diff_str = "-"
            else:
                diff_pct = abs(db_val - manual_val) / max(abs(manual_val), 1e-9) * 100
                status = "OK" if diff_pct < 0.1 else "MISMATCH"
                diff_str = f"{diff_pct:.4f}%"
                if diff_pct >= 0.1:
                    all_ok = False
            print(f"{cid:>10} | {metric:<18} | {str(db_val):>12} | {str(manual_val):>12} | {diff_str:>10} | {status}")

    conn.close()
    print("-" * 90)
    print("Spot-check result:", "ALL WITHIN 0.1% TOLERANCE" if all_ok else "MISMATCHES FOUND — investigate")


if __name__ == "__main__":
    main()
