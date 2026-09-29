import pandas as pd
RULES=[(f'DQ-{i:02d}', 'ERROR' if i%2 else 'WARNING') for i in range(1,15)]
def validate_rule(df,rule_id):
    """Return a violation record for a named DQ rule when its input is empty."""
    return {'rule_id':rule_id,'severity':dict(RULES).get(rule_id,'ERROR'),'violated':df.empty}
