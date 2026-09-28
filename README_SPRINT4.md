# Sprint 4 — Streamlit Dashboard + Valuation

This is an **overlay package** for the existing `serina-33/nifty100-etl` repository. Extract it into the repository root and allow the folders to merge. It adds the Sprint 4 dashboard and valuation module without replacing your existing Sprint 1–3 data.

## 1. Copy the files
Extract the ZIP directly into your existing project folder, for example:
`E:\nifty100-etl-sprint1\nifty100-etl`

## 2. Activate your venv (Windows PowerShell)
```powershell
cd E:\nifty100-etl-sprint1\nifty100-etl
.\venv\Scripts\Activate.ps1
```
If PowerShell blocks activation, run the commands without activation using `venv\Scripts\python.exe`.

## 3. Install Sprint 4 dependencies
```powershell
python -m pip install -r requirements_sprint4.txt
```

## 4. Verify Sprint 1–3 database
```powershell
python scripts/verify_sprint4.py
```
You should see `Companies: 92` and `Python compile check: PASS`.

## 5. Generate valuation files
The module reads `nifty100.db` and, when available, `market_cap.xlsx` from the project root or `data/raw/`.
```powershell
python -m src.analytics.valuation
```
Expected outputs:
- `output/valuation_summary.xlsx` — one row per company, with the required valuation columns.
- `output/valuation_flags.csv` — only Caution/Discount rows.

## 6. Start the dashboard
```powershell
python -m streamlit run src/dashboard/app.py
```
Open `http://localhost:8501`.

## 7. Sprint 4 screens
1. Home
2. Company Profile
3. Screener
4. Peer Comparison
5. Trends
6. Sector Analytics
7. Capital Allocation
8. Annual Reports

## 8. Git commit
After verifying the dashboard:
```powershell
git status
git add src/dashboard src/analytics/valuation.py scripts/run_sprint4.py scripts/verify_sprint4.py requirements_sprint4.txt .streamlit output/valuation_summary.xlsx output/valuation_flags.csv
git commit -m "Complete Sprint 4 dashboard and valuation"
git push origin main
```

**Important:** do not delete your existing `nifty100.db`, `data/raw`, `output`, or Sprint 1–3 files. This ZIP is intended to be merged into the current project.
