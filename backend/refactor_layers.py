import os
import re

backend_dir = r'c:\Users\prana\Desktop\DigiZafe\backend\app'

files = [
    r'connectors\impl\dark_constrained\public_index.py',
    r'connectors\impl\deep\common_crawl.py',
    r'connectors\impl\deep\wayback.py',
    r'connectors\impl\surface\crtsh.py',
    r'connectors\impl\surface\github_connector.py',
    r'connectors\impl\surface\gravatar.py',
    r'connectors\impl\surface\pwned_passwords.py',
    r'connectors\impl\surface\rdap.py',
    r'connectors\impl\surface\serp_ddg.py',
    r'connectors\impl\surface\username_presence.py',
    r'connectors\impl\surface\xposedornot.py',
    r'connectors\sdk\types.py',
    r'domain\amber_layers.py'
]

for rel_path in files:
    full_path = os.path.join(backend_dir, rel_path)
    if not os.path.exists(full_path):
        continue
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    
    if rel_path.endswith('amber_layers.py'):
        content = re.sub(r'class ExposureLayer\(str, Enum\):\n\s+SURFACE = "surface"\n\s+DEEP = "deep"\n\s+CONSTRAINED_DARK = "constrained_dark"\n', '', content)
        content = content.replace('from typing import Any', 'from typing import Any\nfrom app.domain.exposure_layers import ExposureLayer')
    elif rel_path.endswith('types.py'):
        content = re.sub(r'class ConnectorLayer\(str, Enum\):\n\s+SURFACE = "surface"\n\s+DEEP = "deep"\n\s+CONSTRAINED_DARK = "constrained_dark"\n', '', content)
        content = content.replace('ConnectorLayer', 'ExposureLayer')
        content = 'from app.domain.exposure_layers import ExposureLayer\n' + content
    else:
        # connectors
        content = content.replace('ConnectorLayer,', '')
        content = content.replace('ConnectorLayer', 'ExposureLayer')
        content = 'from app.domain.exposure_layers import ExposureLayer\n' + content
        content = re.sub(r'from app\.connectors\.sdk\.types import\s*\n', '', content)

    if original != content:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('Updated', rel_path)
