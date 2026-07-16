import csv
def load_scope_triggers(csv_path):
    triggers = {'target_start': [], 'target_end': [], 'wait_start': [], 'wait_end': [], 'flip_start': [], 'flip_end': [], 'night_end': []}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader, []) 
        for row in reader:
            if not row: continue
            event = str(row[0]).strip().lower()
            for val in row[1:]:
                val = str(val).strip().lower()
                if not val or val == 'nan' or 'note' in val: continue
                
                if "xxx" in val: clean = val.split("xxx")[0].strip()
                elif ":" in val and any(x in event for x in ["target", "shooting", "completed"]): clean = val.split(":")[0].strip() + ":"
                else: clean = val.strip()
                    
                if "wait start" in event or "wait started" in event: triggers['wait_start'].append(clean)
                elif "wait end" in event or "wait ended" in event: triggers['wait_end'].append(clean)
                elif "flip start" in event or "meridian flip start" in event: triggers['flip_start'].append(clean)
                elif "flip end" in event or "meridian flip end" in event: triggers['flip_end'].append(clean)
                elif "night" in event and ("finish" in event or "end" in event): triggers['night_end'].append(clean)
                elif "start" in event or "new target" in event or "imaging new" in event: triggers['target_start'].append(clean)
                elif "finish" in event or "complet" in event or "end" in event or "shooting" in event: triggers['target_end'].append(clean)
    return triggers
import pprint
print("FRA400")
pprint.pprint(load_scope_triggers("data/FRA400-Table 1.csv"))
print("75Q")
pprint.pprint(load_scope_triggers("data/75Q-Table 1.csv"))
