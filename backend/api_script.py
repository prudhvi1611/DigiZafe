import urllib.request
import json
import uuid

base_url = "http://localhost:8000/api/v1"

# 0. Register user
email = f"test_{uuid.uuid4()}@example.com"
password = "SecurePassword123!"

req = urllib.request.Request(f"{base_url}/auth/register", method="POST", headers={"Content-Type": "application/json"})
req.data = json.dumps({"email": email, "password": password}).encode("utf-8")
try:
    with urllib.request.urlopen(req) as response:
        print("Registered user:", email)
except Exception as e:
    print("Error registering:", e.read().decode() if hasattr(e, 'read') else e)
    exit(1)

# Login
req = urllib.request.Request(f"{base_url}/auth/login/json", method="POST", headers={"Content-Type": "application/json"})
req.data = json.dumps({"email": email, "password": password}).encode("utf-8")
try:
    with urllib.request.urlopen(req) as response:
        login_data = json.loads(response.read().decode())
        token = login_data["access_token"]
        print("Logged in successfully!")
except Exception as e:
    print("Error logging in:", e.read().decode() if hasattr(e, 'read') else e)
    exit(1)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

# 1. Add identifier
req = urllib.request.Request(f"{base_url}/identifiers", method="POST", headers=headers)
req.data = json.dumps({"type": "email", "value": email}).encode("utf-8")
try:
    with urllib.request.urlopen(req) as response:
        ident = json.loads(response.read().decode())
        ident_id = ident["id"]
        print("Created ident:", ident_id)
except Exception as e:
    print("Error creating ident:", e.read().decode() if hasattr(e, 'read') else e)
    exit(1)

# 2. Start verify
req = urllib.request.Request(f"{base_url}/identifiers/{ident_id}/verify/start", method="POST", headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        verify_data = json.loads(response.read().decode())
        challenge_id = verify_data["challenge_id"]
        dev_code = verify_data.get("dev_code")
        print("Verify start:", verify_data)
        if not dev_code:
            print("ERROR: Dev code not returned!")
            exit(1)
except Exception as e:
    print("Error starting verify:", e.read().decode() if hasattr(e, 'read') else e)
    exit(1)

# 3. Confirm verify
req = urllib.request.Request(f"{base_url}/identifiers/{ident_id}/verify/confirm?challenge_id={challenge_id}", method="POST", headers=headers)
req.data = json.dumps({"code": dev_code}).encode("utf-8")
try:
    with urllib.request.urlopen(req) as response:
        confirm_data = json.loads(response.read().decode())
        print("Verify confirm:", confirm_data)
except Exception as e:
    print("Error confirming verify:", e.read().decode() if hasattr(e, 'read') else e)
    exit(1)

# 4. Start scan
req = urllib.request.Request(f"{base_url}/scans", method="POST", headers=headers)
req.data = json.dumps({"identifier_id": ident_id, "layers": ["surface"]}).encode("utf-8")
try:
    with urllib.request.urlopen(req) as response:
        scan_data = json.loads(response.read().decode())
        print("Scan start:", scan_data)
except Exception as e:
    print("Error starting scan:", e.read().decode() if hasattr(e, 'read') else e)
    exit(1)
