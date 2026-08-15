from app.security.password import hash_password, verify_password


def test_hash_and_verify():
    h = hash_password("correct-horse-battery-staple-99")
    assert verify_password("correct-horse-battery-staple-99", h)
    assert not verify_password("wrong", h)
