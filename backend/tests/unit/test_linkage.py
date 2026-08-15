from app.domain.linkage import IdentifierView, score_pair, match_weight_to_prob, build_edges


def test_match_weight_to_prob_mid():
    assert abs(match_weight_to_prob(0.0) - 0.5) < 1e-9
    assert match_weight_to_prob(10) > 0.99


def test_same_user_email_username_link():
    weights = {
        "prior_match_prob": 0.02,
        "comparisons": {
            "same_user_ownership": {"agree_weight": 6.0},
            "type_pair": {"email_github_username": 1.0, "default": 0.3},
            "canonical_similarity": {"exact": 5.0, "substring": 1.0, "none": -1.5, "local_part_match": 2.5},
            "shared_finding_sources": {"per_shared_source": 0.6, "cap": 3.0},
            "shared_breach_names": {"per_shared_breach": 0.4, "cap": 2.5},
            "profile_url_overlap": {"agree": 2.0, "disagree": 0.0},
        },
    }
    a = IdentifierView("1", "email", "alice@example.com", finding_sources=["xposedornot"], breach_names=["Adobe"])
    b = IdentifierView("2", "github_username", "alice", finding_sources=["github", "xposedornot"], breach_names=["Adobe"])
    r = score_pair(a, b, weights, auto_link_prob=0.95, review_prob=0.7, collision_flag_prob=0.5)
    assert r.match_prob > 0.5
    assert r.decision in {"auto_link", "review", "weak"}
