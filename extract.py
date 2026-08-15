import sys
import os
from pathlib import Path

lines = Path('Sprint10.md').read_text(encoding='utf-8').splitlines()

current_file = None
in_code_block = False
code_content = []

for line in lines:
    if line.startswith('## ') or line.startswith('### '):
        if '`' in line:
            parts = line.split('`')
            if len(parts) >= 3:
                if 'Alembic migration' in line or '.env.example' in line or 'docker-compose.yml' in line:
                    print(f'Skipping file: {parts[1]}')
                    current_file = None
                else:
                    current_file = parts[1]
                    in_code_block = False
                    code_content = []
                    print(f'Found NEW file: {current_file}')
                continue
    
    if current_file:
        if line.startswith('```'):
            if not in_code_block:
                in_code_block = True
            else:
                in_code_block = False
                Path(current_file).parent.mkdir(parents=True, exist_ok=True)
                with open(current_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(code_content) + '\n')
                print(f'Wrote {current_file}')
                current_file = None
        elif in_code_block:
            code_content.append(line)
