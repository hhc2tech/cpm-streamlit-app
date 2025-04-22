
def parse_logic_constraints(constraint_str):
    constraints = []
    if constraint_str:
        items = [s.strip() for s in constraint_str.split(',') if s.strip()]
        for item in items:
            if len(item) >= 4:
                constraints.append({
                    'predecessor': item[:2].strip(),
                    'type': item[2:4].strip(),
                    'lag': int(item[4:].strip()) if len(item) > 4 else 0
                })
    return constraints
