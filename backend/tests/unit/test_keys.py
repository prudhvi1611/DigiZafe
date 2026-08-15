from app.security.keys import KeyService


def test_encrypt_decrypt_roundtrip(tmp_path, monkeypatch):
    keyfile = tmp_path / "master.key"
    monkeypatch.setenv("MASTER_KEY_FILE", str(keyfile))
    # reset singleton if needed
    from app.security import keys
    keys._key_service = None

    ks = KeyService()
    blob = ks.encrypt_str("hello-mfa-secret", aad=b"user-1")
    assert ks.decrypt_str(blob, aad=b"user-1") == "hello-mfa-secret"

    idx1 = ks.blind_index("User@Example.com")
    idx2 = ks.blind_index("user@example.com")
    assert idx1 == idx2
