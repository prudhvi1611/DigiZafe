import urllib.request
import json
import uuid
import sys

base_url = "http://localhost:8000/api/v1"

def req(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(f"{base_url}{path}", method=method, headers=headers)
    if data:
        r.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(r) as res:
            if res.status == 204:
                return {}
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "body": e.read().decode()}
    except Exception as e:
        return {"error": True, "status": 500, "body": str(e)}

# 1. Register User A and User B
email_a = f"test_a_{uuid.uuid4()}@example.com"
email_b = f"test_b_{uuid.uuid4()}@example.com"
pw = "SecurePassword123!"

req("/auth/register", method="POST", data={"email": email_a, "password": pw})
req("/auth/register", method="POST", data={"email": email_b, "password": pw})

token_a = req("/auth/login/json", method="POST", data={"email": email_a, "password": pw})["access_token"]
token_b = req("/auth/login/json", method="POST", data={"email": email_b, "password": pw})["access_token"]

print("--- Positive Journey ---")
ident_a = req("/identifiers", method="POST", data={"type": "email", "value": email_a}, token=token_a)
ident_id = ident_a["id"]
print(f"Created Ident A: {ident_id}")

verify_start = req(f"/identifiers/{ident_id}/verify/start", method="POST", token=token_a)
req(f"/identifiers/{ident_id}/verify/confirm?challenge_id={verify_start['challenge_id']}", method="POST", data={"code": verify_start['dev_code']}, token=token_a)
print("Verified Ident A")

scan_a = req("/scans", method="POST", data={"identifier_id": ident_id, "layers": ["surface"]}, token=token_a)
print(f"Scan A Started: {scan_a.get('id', scan_a)}")

print("\n--- Negative Journeys ---")
# Unverified blocked
email_unv = f"unverified_{uuid.uuid4()}@example.com"
ident_unv = req("/identifiers", method="POST", data={"type": "email", "value": email_unv}, token=token_a)
scan_unv = req("/scans", method="POST", data={"identifier_id": ident_unv["id"], "layers": ["surface"]}, token=token_a)
if scan_unv.get("error"):
    print(f"Unverified blocked successfully: {scan_unv['status']}")
else:
    print("FAIL: Unverified scan allowed!")
    sys.exit(1)

# Cross user access denied
scan_cross = req("/scans", method="POST", data={"identifier_id": ident_id, "layers": ["surface"]}, token=token_b)
if scan_cross.get("error"):
    print(f"Cross-user access denied successfully: {scan_cross['status']}")
else:
    print("FAIL: Cross-user scan allowed!")
    sys.exit(1)

# Deep without consent
scan_deep = req("/scans", method="POST", data={"identifier_id": ident_id, "layer_scope": "deep"}, token=token_a)
if scan_deep.get("error"):
    print(f"Deep without consent blocked successfully: {scan_deep['status']}")
else:
    print("FAIL: Deep scan allowed without consent!")
    sys.exit(1)

print("\nAll journeys completed successfully!")
sys.exit(0)
