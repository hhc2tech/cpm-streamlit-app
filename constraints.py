import pandas as pd
import re

def parse_logic_constraints(constraints_str):
    if pd.isna(constraints_str) or constraints_str.strip() == "":
        return []
    relations = []
    parts = constraints_str.split(';')
    for part in parts:
        match = re.match(r'([A-Za-z0-9_]+)\[(FS|SS|FF|SF)([+-]\d+)?\]', part.strip())
        if match:
            pred, relation, lag = match.groups()
            relations.append({
                'predecessor': pred,
                'type': relation,
                'lag': int(lag) if lag else 0
            })
    return relations
