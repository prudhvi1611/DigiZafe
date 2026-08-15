from app.domain.narrative import FactsPack, build_deterministic_narrative


def test_deterministic_mentions_score():
    facts = FactsPack(
        score_combined=6.4,
        severity="medium",
        score_confirmed=6.0,
        score_possible=1.2,
        vector="PDSS:pdss-v1.0.0/SC:6.4/SV:medium",
        explanation_summary="Top driver: Breach Adobe",
        model_version="pdss-v1.0.0",
        contributions=[{"source": "xposedornot", "title": "Breach: Adobe", "weighted_score": 2.1}],
        counterfactuals=[{"narrative": "If Adobe remediated, score would drop."}],
        attributions=["Data: XposedOrNot"],
        open_recommendation_titles=["Change passwords on breached accounts"],
    )
    text = build_deterministic_narrative(facts)
    assert "6.4" in text
    assert "Adobe" in text or "xposedornot" in text.lower()
    assert "Closed loop" in text or "closed loop" in text.lower()
