from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
req=ROOT/'requirements_sprint4.txt'
print('Install Sprint 4 dependencies with:')
print(f'{sys.executable} -m pip install -r {req}')
print('\nGenerating valuation outputs...')
subprocess.run([sys.executable,'-m','src.analytics.valuation'],cwd=ROOT,check=True)
print('\nRun dashboard with:')
print(f'{sys.executable} -m streamlit run src/dashboard/app.py')
