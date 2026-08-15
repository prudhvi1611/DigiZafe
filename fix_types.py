import re

with open('Sprint9.md', 'r', encoding='utf-8') as f:
    text = f.read()

types_9 = re.search(r'## 12\. NEW: `frontend/src/lib/types\.ts`(.*?)\n```typescript\n(.*?)\n```', text, re.DOTALL)
content_9 = types_9.group(2) if types_9 else ''

with open('Sprint10.md', 'r', encoding='utf-8') as f:
    text = f.read()

types_10 = re.search(r'## 3\. UPDATE: `frontend/src/lib/types\.ts`(.*?)\n```typescript\n(.*?)\n```', text, re.DOTALL)
content_10 = types_10.group(2) if types_10 else ''

with open('frontend/src/lib/types.ts', 'w', encoding='utf-8') as f:
    f.write(content_9 + "\n" + content_10)

print(f"Wrote {len(content_9.splitlines())} lines from Sprint 9 and {len(content_10.splitlines())} lines from Sprint 10.")
