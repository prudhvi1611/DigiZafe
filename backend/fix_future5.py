import os
import glob

backend_dir = r'c:\Users\prana\Desktop\DigiZafe\backend\app'
for file in glob.glob(os.path.join(backend_dir, '**', '*.py'), recursive=True):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'from __future__ import annotations' in content:
        lines = content.split('\n')
        new_lines = [l for l in lines if 'from __future__ import annotations' not in l]
        
        insert_idx = 0
        if new_lines and new_lines[0].startswith('"""'):
            if new_lines[0].strip().endswith('"""') and len(new_lines[0].strip()) > 3:
                # Single line docstring
                insert_idx = 1
            else:
                # Multi-line docstring
                for j in range(1, len(new_lines)):
                    if new_lines[j].strip().endswith('"""'):
                        insert_idx = j + 1
                        break
        
        new_lines.insert(insert_idx, 'from __future__ import annotations')
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        print('Fixed properly:', file)
