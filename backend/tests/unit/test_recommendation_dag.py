from app.domain.recommendation import (
    FindingLite,
    build_recommendations,
    topo_sort_codes,
    RecommendationDraft,
    recommend_freeze,
)


def _catalog():
    return {
        "priority_formula": {
            "urgency_weight": 0.45,
            "roi_weight": 0.4,
            "effort_penalty": 0.15,
            "pdss_marginal_boost": 0.35,
        },
        "freeze_recommend_rule": {
            "min_severity_hint": ["high", "critical"],
            "attribute_keywords": ["password", "ssn"],
        },
        "templates": [
            {
                "code": "change_password_breached",
                "lane": "guided",
                "title": "Change passwords",
                "summary": "x",
                "urgency_base": 0.95,
                "effort_hours": 0.5,
                "roi_weight": 1.0,
                "depends_on": [],
                "triggers": {"kinds": ["breach"], "min_severity": "medium"},
                "steps": ["a"],
                "playbook_key": "guided.password_reset",
            },
            {
                "code": "enable_mfa",
                "lane": "guided",
                "title": "Enable MFA",
                "summary": "y",
                "urgency_base": 0.85,
                "effort_hours": 0.25,
                "roi_weight": 0.85,
                "depends_on": ["change_password_breached"],
                "triggers": {"kinds": ["breach"], "min_severity": "low"},
                "steps": ["b"],
                "playbook_key": "guided.mfa",
            },
            {
                "code": "credit_freeze",
                "lane": "guided",
                "title": "Freeze",
                "summary": "z",
                "urgency_base": 0.9,
                "effort_hours": 1.0,
                "roi_weight": 0.95,
                "depends_on": [],
                "triggers": {
                    "kinds": ["breach"],
                    "min_severity": "high",
                    "attribute_contains": ["password"],
                },
                "steps": ["c"],
                "links": [],
                "playbook_key": "guided.credit_freeze",
            },
        ],
    }


def test_topo_mfa_after_password():
    findings = [
        FindingLite(
            id="1",
            kind="breach",
            source="xposedornot",
            title="Adobe",
            severity_hint="high",
            confidence=0.9,
            track="confirmed",
            attributes={"xposed_data": "Passwords", "password_risk": "easytocrack"},
        )
    ]
    drafts = build_recommendations(_catalog(), findings, score_combined=6.5)
    codes = [d.code for d in drafts]
    assert "change_password_breached" in codes
    assert "enable_mfa" in codes
    # password before mfa in DAG order
    assert codes.index("change_password_breached") < codes.index("enable_mfa")


def test_recommend_freeze_high():
    findings = [
        FindingLite(
            id="1",
            kind="breach",
            source="xposedornot",
            title="X",
            severity_hint="high",
            confidence=0.9,
            track="confirmed",
            attributes={"xposed_data": "Passwords"},
        )
    ]
    assert recommend_freeze(findings, _catalog()["freeze_recommend_rule"]) is True
