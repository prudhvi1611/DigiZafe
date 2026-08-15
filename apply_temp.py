import os

def append_to_file(filepath, content):
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write('\n' + content + '\n')
    print(f"Appended to {filepath}")

def overwrite_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Overwrote {filepath}")

def replace_in_file(filepath, old_text, new_text):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    if old_text in text:
        text = text.replace(old_text, new_text)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Replaced in {filepath}")
    else:
        print(f"WARNING: Could not find text in {filepath}")

# 1. registry.py (full replacement)
with open('backend/app/connectors/registry.py.temp11', 'r', encoding='utf-8') as f:
    overwrite_file('backend/app/connectors/registry.py', f.read())

# 2. ScansPage.tsx (full replacement)
with open('frontend/src/features/scans/ScansPage.tsx.temp11', 'r', encoding='utf-8') as f:
    overwrite_file('frontend/src/features/scans/ScansPage.tsx', f.read())

# 3. types.ts (append)
with open('frontend/src/lib/types.ts.temp11', 'r', encoding='utf-8') as f:
    append_to_file('frontend/src/lib/types.ts', f.read())

# 4. test_findings_normalize.py (append)
with open('backend/tests/unit/test_findings_normalize.py.temp11', 'r', encoding='utf-8') as f:
    append_to_file('backend/tests/unit/test_findings_normalize.py', f.read())

# 5. free-sources.md (append)
with open('docs/free-sources.md.temp11', 'r', encoding='utf-8') as f:
    append_to_file('docs/free-sources.md', f.read())

# 6. pdss-v1.md (append)
with open('docs/model-cards/pdss-v1.md.temp11', 'r', encoding='utf-8') as f:
    append_to_file('docs/model-cards/pdss-v1.md', f.read())

# 7. main.py (replace imports and router)
replace_in_file('backend/app/main.py',
"""from app.api.v1 import (
    health,
    auth,
    identifiers,
    connectors,
    scans,
    identity,
    scores,
    recommendations,
    alerts,
    remediation,
    privacy,
)""",
"""from app.api.v1 import (
    health,
    auth,
    identifiers,
    connectors,
    scans,
    identity,
    scores,
    recommendations,
    alerts,
    remediation,
    privacy,
    layers,
)""")

replace_in_file('backend/app/main.py',
    'app.include_router(privacy.router, prefix="/api/v1/privacy", tags=["privacy"])',
    'app.include_router(privacy.router, prefix="/api/v1/privacy", tags=["privacy"])\napp.include_router(layers.router, prefix="/api/v1/layers", tags=["layers"])'
)

