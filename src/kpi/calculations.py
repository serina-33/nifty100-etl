import math

def roe(net_profit,equity):
    """Calculate ROE or return None for non-positive equity."""
    return None if equity is None or equity<=0 or net_profit is None else net_profit/equity*100

def debt_to_equity(debt,equity):
    """Calculate debt-to-equity with zero for debt-free companies."""
    if debt is None: return None
    if debt==0: return 0.0
    if equity is None or equity<=0: return None
    return debt/equity

def icr(ebit,interest):
    """Calculate interest coverage or None when interest is zero."""
    if interest in (None,0): return None
    return ebit/interest

def cagr(start,end,years):
    """Calculate CAGR while handling turnaround and decline-to-loss cases."""
    if years<=0 or start is None or end is None: return None
    if start>0 and end>0: return ((end/start)**(1/years)-1)*100
    return None

def cfo_quality(cfo_pat_values):
    """Calculate average CFO/PAT quality score."""
    vals=[x for x in cfo_pat_values if x is not None and math.isfinite(x)]
    return sum(vals)/len(vals) if vals else None
