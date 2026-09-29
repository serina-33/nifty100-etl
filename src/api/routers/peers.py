from fastapi import APIRouter,HTTPException
from src.common import connect,find_table,tables,read_table,col
router=APIRouter(prefix='/peers',tags=['peers'])
def peer_table():
    """Load peer percentile data from the project database."""
    con=connect(); t=find_table(tables(con),['peer_percentiles','peer_comparison','peer_engine']); d=read_table(t,con) if t else None; con.close(); return d
@router.get('/{group_name}')
def peer_group(group_name:str):
    """Return companies and percentile ranks for a peer group."""
    d=peer_table()
    if d is None or d.empty: raise HTTPException(404,detail='Peer group data not found')
    gc=col(d,['group_name','peer_group','group']); x=d[d[gc].astype(str).str.lower()==group_name.lower()] if gc else d.iloc[0:0]
    if x.empty: raise HTTPException(404,detail='Unknown group')
    return x.astype(object).where(x.notna(),None).to_dict('records')
