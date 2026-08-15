import os
import glob
backend_dir = r'c:\Users\prana\Desktop\DigiZafe\backend\app'
python_files = glob.glob(os.path.join(backend_dir, '**', '*.py'), recursive=True)

for file in python_files:
    with open(file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    has_future = False
    for line in lines:
        if 'from __future__ import annotations' in line:
            has_future = True
        else:
            new_lines.append(line)
            
    if has_future:
        # insert at top
        insert_idx = 0
        if new_lines and new_lines[0].startswith('"""'):
            for j in range(1, len(new_lines)):
                if new_lines[j].strip().endswith('"""'):
                    insert_idx = j + 1
                    break
        new_lines.insert(insert_idx, 'from __future__ import annotations\n')
        with open(file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print('Fixed properly', file)
