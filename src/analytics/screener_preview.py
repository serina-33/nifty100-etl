"""
screener_preview.py — Sprint 2, Day 14 deliverable
Quick screener filter: ROE > 15% and D/E < 1, using each company's most
recent year. Exit criterion: result count should be between 15 and 50
companies and the list should make business sense.
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT c.company_id, c.company_name, c.sector, fr.year,
               fr.return_on_equity_pct, fr.debt_to_equity
        FROM financial_ratios fr
        JOIN companies c ON c.company_id = fr.company_id
        INNER JOIN (
            SELECT company_id, MAX(year) AS max_year FROM financial_ratios GROUP BY company_id
        ) latest ON fr.company_id = latest.company_id AND fr.year = latest.max_year
        WHERE fr.return_on_equity_pct > 15 AND fr.debt_to_equity < 1
        ORDER BY fr.return_on_equity_pct DESC
    """).fetchall()
    conn.close()

    print(f"Screener: ROE > 15% AND D/E < 1")
    print(f"Result count: {len(rows)} companies (target range: 15-50)")
    print("-" * 80)
    for cid, name, sector, year, roe, de in rows:
        print(f"{name:<20} | {sector:<18} | year={year} | ROE={roe:>7.2f}% | D/E={de:.2f}")

    in_range = 15 <= len(rows) <= 50
    print("-" * 80)
    print("Result count within expected range:" , "YES" if in_range else "NO -- review filter thresholds or data")


if __name__ == "__main__":
    main()
