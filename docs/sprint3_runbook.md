# Sprint 3 — Runbook

This add-on is designed for `serina-33/nifty100-etl` after Sprint 1 and Sprint 2.

## Install

The existing requirements already include pandas, numpy, openpyxl and matplotlib. Install PyYAML if it is missing:

```powershell
pip install pyyaml
```

## Run

From the repository root:

```powershell
python scripts/run_sprint3.py
```

## Outputs

- `output/screener_output.xlsx` — six preset sheets with threshold highlighting.
- `output/peer_comparison.xlsx` — eleven peer-group sheets with percentile bands and median rows.
- `reports/radar_charts/*.png` — one chart per company.
- SQLite table `peer_percentiles`.

## Tests

```powershell
pytest tests/screener tests/peer -v
```

The runner reads `data/raw/11_peer_groups.xlsx` when it contains a peer-group assignment column. If that workbook cannot be interpreted as an 11-group assignment, the runner creates deterministic fallback buckets so the Sprint 3 deliverable remains runnable.
