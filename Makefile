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

## Computes/refreshes derived financial ratios (used by later sprints too)
ratios:
	$(PYTHON) -c "print('Ratios already loaded via 10_financial_ratios.xlsx in Sprint 1; \
Sprint 2+ will add derived-ratio computation here.')"

## Day 07 — run the 35+ unit test suite
test:
	$(PYTHON) -m pytest tests/etl/ -v

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
