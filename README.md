# Nifty100 ETL — Sprint 1 (Day 01–07) + Bluestock Internship Prerequisites (Week 2)

This project contains two things:

1. **Sprint 1 of the Nifty100 Data Ingestion & ETL epic** — a complete, runnable ETL pipeline: 12 synthetic source files → validated 11-table SQLite database (`nifty100.db`), with 16 automated data-quality rules and 45 passing unit tests.
2. **The Week 2 prerequisite learning deliverables** for the Bluestock Fintech internship (stock market fundamentals, a REST API assignment, a Git/GitHub guide, a software-architecture note, and a FinTech research report).

## Quick start

```bash
pip install -r requirements.txt --break-system-packages   # or: make setup (creates a venv)
python3 scripts/generate_source_data.py                    # generates the 12 synthetic source .xlsx files
python3 src/etl/loader.py                                  # builds nifty100.db + output/load_audit.csv
python3 src/etl/validator.py                                # runs DQ-01..DQ-16 -> output/validation_failures.csv
python3 -m pytest tests/etl/ -v                             # 45 unit tests
```

Or via Makefile: `make load`, `make validate`, `make test`, `make report`.

## Sprint 1 — exit criteria (all verified passing)

| Criterion | Result |
|---|---|
| `SELECT COUNT(*) FROM companies` | **92** ✅ |
| `PRAGMA foreign_key_check` | **0 rows** ✅ |
| `load_audit.csv` CRITICAL rejections | **0** ✅ |
| Unit tests | **45/45 passing** (target: 35+) ✅ |
| DQ-01..DQ-16 CRITICAL failures | **0** ✅ (7 WARNING-level findings, expected — see below) |

## Project layout

```
├── data/raw/                  12 synthetic source .xlsx files (7 core + 5 supplementary)
├── db/schema.sql               11-table SQLite schema, PK/FK, PRAGMA foreign_keys = ON
├── src/etl/
│   ├── normaliser.py            normalize_year(), normalize_ticker()
│   ├── loader.py                 loads all 12 files -> nifty100.db, writes load_audit.csv
│   └── validator.py               DQ-01..DQ-16 -> validation_failures.csv
├── tests/etl/                  45 unit tests (pytest)
├── notebooks/exploratory_queries.sql   10 verified queries
├── output/{load_audit.csv, validation_failures.csv}
├── scripts/generate_source_data.py     synthetic data generator (stands in for real Nifty100 extracts)
├── Makefile, requirements.txt, .env.example    Day 01 environment setup
├── diagrams/data_flow_architecture.svg
├── docs/                        Week 2 learning deliverables (see below)
└── api_assignment/              REST API & JSON assignment (calls a real public API)
```

## Note on the source data

No real Nifty100 Excel extracts were provided, so `scripts/generate_source_data.py` generates **synthetic but structurally realistic** data — 92 companies, 14–16 years of financials each (with deliberately thin/short histories on a subset of companies to exercise the Day 06 manual-review step), messy year/ticker formats to exercise the normaliser, and a handful of intentionally-injected data quality issues (imbalanced balance sheets, bad URLs, dividend payouts >100%, etc.) so the 16 DQ rules have real findings to report — matching the WARNING-level findings you'd expect from real-world financial data. Swap in real source files with the same column names and the pipeline runs unchanged.

## Sprint 2 — Financial Ratio Engine (Day 08–14)

Builds on Sprint 1's database to compute 50+ KPIs across all 92 companies.

```bash
python3 scripts/patch_companies_sprint2.py    # adds broad_sector + supplementary pre-computed ratios file
python3 src/analytics/populate_ratios.py       # runs the full engine, rebuilds financial_ratios table
python3 scripts/patch_companies_sprint2.py     # re-run: builds a realistic pre-computed baseline from the fresh engine output
python3 -m pytest tests/kpi/ -v                # 55 unit tests (target: 20+)
python3 src/analytics/log_edge_cases.py        # Day 13: ROCE/ROE cross-check -> output/ratio_edge_cases.log
python3 src/analytics/spot_check.py            # Day 12/14: manual recompute check (target: <0.1% diff)
python3 src/analytics/screener_preview.py      # Day 14: ROE>15% & D/E<1 screener (target: 15-50 results)
```

Or via `make ratios`.

**Why `patch_companies_sprint2.py` runs twice:** the first pass adds the `broad_sector` classification (Financials vs Non-Financials) needed by the ratio engine's D/E flag suppression logic. The second pass (after `populate_ratios.py` has run) builds the Day 13 pre-computed vendor-ratio comparison file using the *freshly computed* ROE/ROCE as a realistic baseline (with small vendor-style noise plus 5 deliberately planted anomalies) rather than stale placeholder values.

### Sprint 2 — exit criteria (all verified passing)

| Criterion | Result |
|---|---|
| `SELECT COUNT(*) FROM financial_ratios` | **1,344 rows** (target: ≥1,100) ✅ |
| All 17 KPI/flag columns populated (no null-only columns) | ✅ |
| KPI formula unit tests | **55/55 passing** (target: 20+) ✅ |
| Manual spot-check (ROE + 5yr Revenue CAGR, 3 companies) | **0.0000% diff** (target: <0.1%) ✅ |
| `ratio_edge_cases.log` — every anomaly documented + categorized | **7 anomalies logged**, all 5 planted decimal-scale glitches correctly caught ✅ |
| Financials broad-sector D/E flag suppression | **0 incorrectly flagged** (19 companies classified as Financials) ✅ |
| Screener preview (ROE>15% & D/E<1) | **29 companies** (target: 15-50) ✅ |

### Sprint 2 file layout

```
├── src/analytics/
│   ├── ratios.py             Day 08-09: profitability, leverage, efficiency ratios
│   ├── cagr.py                Day 10: CAGR engine, 6 edge cases
│   ├── cashflow_kpis.py        Day 11: FCF, CFO quality, CapEx intensity, 8-pattern classifier
│   ├── populate_ratios.py       Day 12: runs the full engine -> financial_ratios table
│   ├── log_edge_cases.py         Day 13: ROCE/ROE cross-check -> ratio_edge_cases.log
│   ├── spot_check.py              Day 12/14: manual recompute verification
│   └── screener_preview.py         Day 14: ROE/D-E screener sanity check
├── scripts/patch_companies_sprint2.py   adds broad_sector + pre-computed ratios source file
├── tests/kpi/{test_ratios.py, test_cagr.py, test_cashflow_kpis.py}   55 unit tests
├── output/{capital_allocation.csv, ratio_edge_cases.log}
```

## Week 2 — prerequisite learning deliverables (`docs/`)

| File | Covers |
|---|---|
| `01_stock_market_summary.md` | Stock market fundamentals + a worked financial-statement analysis |
| `02_api_json_assignment.md` | REST APIs & JSON — write-up for `api_assignment/` |
| `03_git_github_assignment.md` | Git & GitHub — concepts + exact commands to version this repo |
| `04_software_architecture.md` | Frontend/backend, client-server, APIs, databases, pipelines, logging, SDLC |
| `05_fintech_research_report.md` | Zerodha research report — data analytics in a real Indian FinTech |

`api_assignment/fetch_api_data.py` actually calls the GitHub Search API, saves the raw JSON (`api_response_raw.json`), and converts it to `github_fintech_repos.csv` — a real, runnable example of the API → JSON → CSV workflow, not a mock.

`diagrams/data_flow_architecture.svg` shows the user-action → frontend → backend API → database → ETL pipeline → dashboard data flow referenced in `04_software_architecture.md`.
