import os
import glob
backend_dir = r'c:\Users\prana\Desktop\DigiZafe\backend\app'
python_files = glob.glob(os.path.join(backend_dir, '**', '*.py'), recursive=True)

for file in python_files:
    with open(file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    future_idx = -1
    for i, line in enumerate(lines):
        if 'from __future__ import annotations' in line:
            future_idx = i
            break
            
    if future_idx > 0:
        line_to_move = lines.pop(future_idx)
        insert_idx = 0
        if lines and lines[0].startswith('\"\"\"'):
            for j in range(1, len(lines)):
                if lines[j].strip().endswith('\"\"\"'):
                    insert_idx = j + 1
                    break
        lines.insert(insert_idx, line_to_move)
        with open(file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print('Fixed future import in', file)
