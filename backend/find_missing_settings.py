import ast
import os
import sys

def get_settings_attributes():
    from app.core.config import get_settings
    settings = get_settings()
    return set(dir(settings))

def find_settings_accesses(directory):
    accesses = set()
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read(), filename=path)
                    except SyntaxError:
                        continue
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute):
                        if isinstance(node.value, ast.Attribute) and node.value.attr == 'settings':
                            if isinstance(node.value.value, ast.Name) and node.value.value.id == 'self':
                                accesses.add(node.attr)
    return accesses

if __name__ == '__main__':
    # Need to add backend to sys.path to import app.core.config
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    try:
        available = get_settings_attributes()
        used = find_settings_accesses('app')
        missing = used - available
        # Also remove magic methods and generic pydantic methods
        missing = {m for m in missing if not m.startswith('_') and m not in ['model_dump', 'model_copy']}
        if missing:
            print(f"MISSING SETTINGS FOUND: {missing}")
            sys.exit(1)
        else:
            print("No missing settings found!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
