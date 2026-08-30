# Git & GitHub — Assignment writeup

## Core concepts

| Term | Meaning |
|---|---|
| Repository (repo) | A folder tracked by Git, containing your project's full version history |
| Clone | Copying a remote repo (e.g. from GitHub) to your local machine |
| Commit | A saved snapshot of changes, with a message describing what changed and why |
| Push | Uploading local commits to the remote repo |
| Pull | Downloading and merging remote changes into your local repo |
| Branch | An independent line of development, used to work on a feature without affecting `main` |
| Pull Request (PR) | A request to merge one branch into another, with room for review/comments before merging |

## Steps to set up this project's repository

```bash
# 1. Initialize the repo (run once, inside the project folder)
cd nifty100-etl
git init
git branch -M main

# 2. Create a .gitignore so generated data/venv/db files aren't committed
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
.env
nifty100.db
data/raw/*.xlsx
output/*.csv
api_assignment/api_response_raw.json
api_assignment/*.csv
EOF

# 3. Stage and make the first commit
git add .
git commit -m "Sprint 1: ETL pipeline, schema, DQ rules, tests, docs"

# 4. Create the remote repo on GitHub (via the GitHub UI or gh CLI), then link it
git remote add origin https://github.com/<your-username>/nifty100-etl.git
git push -u origin main

# 5. Day-to-day workflow on a feature branch
git checkout -b feature/day02-normaliser
# ... make changes ...
git add src/etl/normaliser.py tests/etl/test_normaliser.py
git commit -m "Day 02: add normalize_year/normalize_ticker + 35 unit tests"
git push -u origin feature/day02-normaliser
# Open a Pull Request on GitHub from feature/day02-normaliser -> main, request review, merge

# 6. Keep local main up to date with the remote
git checkout main
git pull origin main
```

## Suggested repository structure (matches this deliverable)

```
nifty100-etl/
├── .env.example
├── .gitignore
├── Makefile
├── requirements.txt
├── db/schema.sql
├── src/etl/{loader.py, normaliser.py, validator.py}
├── tests/etl/{test_normaliser.py, test_pipeline.py}
├── notebooks/exploratory_queries.sql
├── output/{load_audit.csv, validation_failures.csv}
├── docs/  (Week 2 learning deliverables)
├── diagrams/
└── api_assignment/{fetch_api_data.py, github_fintech_repos.csv}
```

## Maintaining version history

Commit early and often, with descriptive messages tied to a specific unit of work (one Sprint day, one bug fix, one feature) rather than one giant "final version" commit. This mirrors exactly how Sprint 1 is broken into Day 01–07 deliverables above — each day's deliverable maps naturally to one or more commits/PRs.
