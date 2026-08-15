import os
import glob
import re

backend_dir = r'c:\Users\prana\Desktop\DigiZafe\backend\app'
python_files = glob.glob(os.path.join(backend_dir, '**', '*.py'), recursive=True)

for file in python_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'from __future__ import annotations' in content:
        # Remove all instances completely
        content = re.sub(r'^[ \t]*from __future__ import annotations[ \t]*\n?', '', content, flags=re.MULTILINE)

        # Re-insert at the top
        lines = content.split('\n')
        
        insert_idx = 0
        if lines and lines[0].startswith('"""'):
            for j in range(1, len(lines)):
                if lines[j].strip().endswith('"""'):
                    insert_idx = j + 1
                    break
        
        lines.insert(insert_idx, 'from __future__ import annotations')
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print('Fixed', file)
