from app.remediation.generators.templates import generate_right_to_know, generate_complaint


def test_ccpa_know():
    g = generate_right_to_know(
        regime="ccpa",
        full_name="Ada Lovelace",
        email="ada@example.com",
        recipient_name="Example Broker",
        include_deletion=True,
    )
    assert "CCPA" in g["subject"] or "California" in g["subject"]
    assert "ada@example.com" in g["body"]
    assert g["deadline_at"] is not None


def test_complaint():
    g = generate_complaint(
        regime="ccpa",
        full_name="Ada",
        email="a@b.com",
        recipient_name="BrokerCo",
        regulator="ca_ag",
        facts="No response after 45 days.",
    )
    assert "complaint" in g["subject"].lower() or "CCPA" in g["subject"]
