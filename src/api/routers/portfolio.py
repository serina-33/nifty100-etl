from fastapi import APIRouter
import pandas as pd
from src.common import OUT
router=APIRouter(prefix='/portfolio',tags=['portfolio'])
@router.get('/stats')
def portfolio_stats():
    """Return portfolio percentile statistics for ten KPIs."""
    p=OUT/'portfolio_stats.csv'
    if not p.exists(): return []
    return pd.read_csv(p).where(pd.notna(pd.read_csv(p)),None).to_dict('records')
