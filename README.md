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
