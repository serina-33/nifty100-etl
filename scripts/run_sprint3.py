"""Sprint 3 master runner.

Run from the repository root:
    python scripts/run_sprint3.py

Prerequisite: Sprint 1 + Sprint 2 have built nifty100.db and financial_ratios.
"""
from __future__ import annotations
import sqlite3, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.screener.engine import load_config, latest_complete_snapshot, run_all_presets
from src.screener.export_screener_xlsx import export_screener_workbook
from src.analytics.peer import build_peer_percentiles
from src.analytics.radar_charts import generate_radar_charts
from src.analytics.export_peer_comparison_xlsx import export_peer_comparison

def main():
    db=ROOT/"nifty100.db"
    if not db.exists():
        raise SystemExit("nifty100.db not found. Complete Sprint 1/2 first.")
    conn=sqlite3.connect(db)
    try:
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "financial_ratios" not in tables:
            raise SystemExit("financial_ratios table not found. Run Sprint 2 ratio engine first.")
        cfg=load_config()
        snap=latest_complete_snapshot(conn)
    finally:
        conn.close()

    print(f"Latest complete snapshot: {len(snap)} companies")
    results=run_all_presets(snap,cfg)
    print("\\nPreset counts:")
    for name,df in results.items():
        print(f"  {name}: {len(df)}")
        if not 5 <= len(df) <= 50:
            print("    WARNING: outside the 5–50 sprint target; review source data/thresholds.")
    screener_path=export_screener_workbook(results)
    print(f"Wrote {screener_path}")

    pct,assignments=build_peer_percentiles()
    print(f"Peer assignments: {assignments.peer_group_name.nunique()} groups / {len(assignments)} assignments")
    print(f"Peer percentile rows: {len(pct)}")
    if assignments.peer_group_name.nunique()!=11:
        raise SystemExit("Sprint 3 requires exactly 11 peer groups.")
    peer_path=export_peer_comparison()
    print(f"Wrote {peer_path}")

    charts=generate_radar_charts(peer_assignments=assignments)
    print(f"Radar charts generated: {len(charts)}")

    print("\\nSPRINT 3 COMPLETE")
    print("Outputs:")
    print("  output/screener_output.xlsx")
    print("  output/peer_comparison.xlsx")
    print("  reports/radar_charts/*.png")
    print("  SQLite table: peer_percentiles")

if __name__=="__main__":
    main()
