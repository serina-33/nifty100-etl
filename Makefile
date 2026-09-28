.PHONY: setup load validate ratios test report dashboard api clean

PYTHON := venv/bin/python3
PIP := venv/bin/pip

## Day 01 — one-time environment setup (venv + 20 libs + dirs)
setup:
	python3 -m venv venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	mkdir -p data/raw output notebooks tests/etl db docs diagrams
	cp -n .env.example .env || true
	@echo "Environment ready. Activate with: source venv/bin/activate"

## Day 05 — generate synthetic source files + full load of all 12 files
load:
	$(PYTHON) scripts/generate_source_data.py
	$(PYTHON) src/etl/loader.py

## Day 03 — run all 16 DQ rules, write output/validation_failures.csv
validate:
	$(PYTHON) src/etl/validator.py

## Sprint 2 — computes 17-column ratio engine for all company-years
ratios:
	$(PYTHON) scripts/patch_companies_sprint2.py
	$(PYTHON) src/analytics/populate_ratios.py
	$(PYTHON) scripts/patch_companies_sprint2.py
	$(PYTHON) src/analytics/log_edge_cases.py
	$(PYTHON) src/analytics/spot_check.py
	$(PYTHON) src/analytics/screener_preview.py

## Day 07 / Day 14 — run the full unit test suite (Sprint 1 + Sprint 2)
test:
	$(PYTHON) -m pytest tests/etl/ tests/kpi/ -v

## Runs the 10 exploratory queries and prints results
report:
	$(PYTHON) -c "\
import sqlite3; \
conn = sqlite3.connect('nifty100.db'); \
sql = open('notebooks/exploratory_queries.sql').read(); \
lines = [l for l in sql.split(chr(10)) if not l.strip().startswith('--')]; \
stmts = [s.strip() for s in chr(10).join(lines).split(';') if s.strip()]; \
[print(f'--- Query {i} ---', *conn.execute(s).fetchall()[:10], sep=chr(10)) for i, s in enumerate(stmts, 1)]"

## Placeholder — Sprint 2+ dashboard module
dashboard:
	@echo "Dashboard module scheduled for a later sprint (not part of Sprint 1 scope)."

## Placeholder — Sprint 2+ API module
api:
	@echo "API module scheduled for a later sprint (not part of Sprint 1 scope)."

## Removes generated DB + outputs so the pipeline can be re-run from scratch
clean:
	rm -f nifty100.db
	rm -f output/*.csv
	rm -rf data/raw/*.xlsx
	@echo "Cleaned generated data. Run 'make load' to rebuild."
