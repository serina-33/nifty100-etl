"""
log_edge_cases.py — Sprint 2, Day 13 deliverable
Cross-checks computed ROCE/ROE (latest year per company) against the
pre-computed vendor-style values in company_precomputed_ratios (see
scripts/patch_companies_sprint2.py), logs every anomaly with a category,
and confirms the Financials broad-sector D/E flag suppression is working.

Run: python3 src/analytics/log_edge_cases.py
Output: output/ratio_edge_cases.log
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_PATH = OUTPUT_DIR / "ratio_edge_cases.log"

ROCE_TOLERANCE_PCT = 5.0


def categorize(computed, source, field_name):
    """
    Simple heuristic categorization, matching the sprint's 3 categories:
      - "unit/version difference": source value looks like a decimal-scale
        error (e.g. 0.52 instead of 52.0) -- computed/source ratio near 100.
      - "data source issue": source value is wildly implausible (negative,
        or an extreme outlier) independent of scale.
      - "formula discrepancy": both values are in a plausible range and
        same order of magnitude, but still differ beyond tolerance --
        suggests the underlying formula/definition differs.
    """
    if source is None or computed is None:
        return "data source issue"
    if source != 0 and abs((computed / source) - 100) < 15:
        return "unit/version difference (likely decimal-scale error, e.g. 0.52 vs 52.0)"
    if source < -50 or source > 500:
        return "data source issue"
    return "formula discrepancy"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    latest_computed = conn.execute("""
        SELECT fr.company_id, fr.year, fr.return_on_equity_pct, fr.return_on_capital_employed_pct
        FROM financial_ratios fr
        INNER JOIN (
            SELECT company_id, MAX(year) AS max_year FROM financial_ratios GROUP BY company_id
        ) latest ON fr.company_id = latest.company_id AND fr.year = latest.max_year
    """).fetchall()

    precomputed = dict(
        (row[0], (row[1], row[2]))
        for row in conn.execute(
            "SELECT company_id, roce_percentage_source, roe_percentage_source FROM company_precomputed_ratios")
    )

    financials_map = dict(conn.execute(
        "SELECT company_id, COALESCE(broad_sector, 'Non-Financials') FROM companies"))
    de_flags = dict(conn.execute(
        "SELECT company_id, high_leverage_flag FROM financial_ratios "
        "WHERE (company_id, year) IN (SELECT company_id, MAX(year) FROM financial_ratios GROUP BY company_id)"))
    de_values = dict(conn.execute(
        "SELECT company_id, debt_to_equity FROM financial_ratios "
        "WHERE (company_id, year) IN (SELECT company_id, MAX(year) FROM financial_ratios GROUP BY company_id)"))

    lines = []
    lines.append("Sprint 2 · Day 13 — Ratio Engine Edge Case Log")
    lines.append("=" * 60)
    lines.append("")
    lines.append("SECTION 1: ROCE / ROE cross-check vs pre-computed vendor source")
    lines.append("-" * 60)

    anomaly_count = 0
    for cid, year, roe_computed, roce_computed in latest_computed:
        roce_source, roe_source = precomputed.get(cid, (None, None))

        if roce_computed is not None and roce_source is not None:
            diff_pct = abs(roce_computed - roce_source) / max(abs(roce_source), 1e-9) * 100
            if diff_pct > ROCE_TOLERANCE_PCT:
                category = categorize(roce_computed, roce_source, "roce")
                anomaly_count += 1
                lines.append(
                    f"[ROCE] company_id={cid}, year={year}: computed={roce_computed}, "
                    f"source={roce_source}, diff={diff_pct:.1f}% -> category: {category}")

        if roe_computed is not None and roe_source is not None:
            diff_pct = abs(roe_computed - roe_source) / max(abs(roe_source), 1e-9) * 100
            if diff_pct > ROCE_TOLERANCE_PCT:
                category = categorize(roe_computed, roe_source, "roe")
                anomaly_count += 1
                lines.append(
                    f"[ROE]  company_id={cid}, year={year}: computed={roe_computed}, "
                    f"source={roe_source}, diff={diff_pct:.1f}% -> category: {category} "
                    f"(note: use ratio-engine value for analytics, source value for display only)")

    lines.append("")
    lines.append(f"Total ROCE/ROE anomalies logged: {anomaly_count}")
    lines.append("")
    lines.append("SECTION 2: Financials broad-sector D/E flag suppression check")
    lines.append("-" * 60)

    financials_ids = [cid for cid, sector in financials_map.items() if sector == "Financials"]
    lines.append(f"Companies classified as Financials broad_sector: {len(financials_ids)}")

    suppressed_correctly = 0
    incorrectly_flagged = 0
    for cid in financials_ids:
        de = de_values.get(cid)
        flagged = de_flags.get(cid)
        if de is not None and de > 5 and not flagged:
            suppressed_correctly += 1
        elif flagged:
            incorrectly_flagged += 1

    lines.append(f"High-D/E Financials companies with flag correctly suppressed: {suppressed_correctly}")
    lines.append(f"Financials companies incorrectly still flagged (should be 0): {incorrectly_flagged}")
    if incorrectly_flagged > 0:
        lines.append(">>> ACTION NEEDED: high_leverage_flag() sector suppression is not working as expected.")
    else:
        lines.append("Sector suppression logic verified correct.")

    LOG_PATH.write_text("\n".join(lines))
    conn.close()

    print(f"Wrote edge case log with {anomaly_count} ROCE/ROE anomalies -> {LOG_PATH}")
    print(f"D/E suppression check: {incorrectly_flagged} incorrectly flagged Financials companies (target: 0)")


if __name__ == "__main__":
    main()
