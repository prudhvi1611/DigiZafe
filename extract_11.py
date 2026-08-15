import os
import re

with open('Sprint11.md', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()

current_file = None
current_content = []
in_block = False
action = None

for line in lines:
    if line.startswith('## ') and '`' in line:
        parts = line.split('`')
        if len(parts) >= 3:
            filename = parts[1]
            if 'UPDATE' in line or 'NEW' in line or 'EXTEND' in line:
                current_file = filename
                current_content = []
                action = 'NEW' if 'NEW' in line and not 'UPDATE' in line else 'UPDATE'
                continue
    
    if current_file:
        if line.startswith('```') and not in_block:
            in_block = True
            continue
        if line.startswith('```') and in_block:
            in_block = False
            content_str = '\n'.join(current_content) + '\n'
            
            if current_file == '.env.example':
                with open('.env', 'a', encoding='utf-8') as out:
                    out.write('\n' + content_str)
                with open('frontend/.env', 'a', encoding='utf-8') as out:
                    out.write('\n' + content_str)
                with open('.env.example', 'a', encoding='utf-8') as out:
                    out.write('\n' + content_str)
                print(f"Appended to env files")
            elif action == 'UPDATE':
                with open(current_file + '.temp11', 'w', encoding='utf-8') as out:
                    out.write(content_str)
                print(f"Wrote to {current_file}.temp11 for manual update")
            else:
                os.makedirs(os.path.dirname(current_file) if os.path.dirname(current_file) else '.', exist_ok=True)
                with open(current_file, 'w', encoding='utf-8') as out:
                    out.write(content_str)
                print(f"Wrote NEW file to {current_file}")
            
            current_file = None
            continue
        
        if in_block:
            current_content.append(line)
