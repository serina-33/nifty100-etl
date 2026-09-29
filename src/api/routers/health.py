import time, sqlite3
from fastapi import APIRouter
from src.common import connect,tables
router=APIRouter(prefix='/health',tags=['health'])
START=time.time()
@router.get('')
def health():
    """Return service status, database row counts, uptime and version."""
    con=connect(); counts={}
    for t in tables(con):
        try: counts[t]=con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        except sqlite3.Error: counts[t]=None
    con.close(); return {'status':'ok','db_row_counts':counts,'uptime_seconds':round(time.time()-START,2),'version':'1.0.0'}
