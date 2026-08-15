import re

def patch_file(filepath, search, replace):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    if search in text:
        text = text.replace(search, replace)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Patched {filepath}")
    else:
        print(f"Could not find search string in {filepath}")

# backend/app/main.py
patch_file(
    'backend/app/main.py',
    '''from app.api.v1 import (
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
)''',
    '''from app.api.v1 import (
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
)'''
)

patch_file(
    'backend/app/main.py',
    'app.include_router(privacy.router, prefix="/api/v1/privacy", tags=["privacy"])',
    '''app.include_router(privacy.router, prefix="/api/v1/privacy", tags=["privacy"])
app.include_router(layers.router, prefix="/api/v1/layers", tags=["layers"])'''
)

# backend/app/connectors/registry.py - wait, what was this?
