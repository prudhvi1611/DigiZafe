"""Grounded narrative: facts pack + deterministic fallback (no LLM required)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SYSTEM_PROMPT = """You are DigiZafe's privacy briefing writer.
You ONLY restate facts provided in the FACTS JSON.
Rules:
- Do NOT invent breaches, scores, brokers, or findings not present in FACTS.
- Do NOT claim removal completed unless FACTS say so.
- Prefer clear, calm, actionable language for a non-expert individual.
- Mention XposedOrNot attribution if FACTS include source xposedornot.
- Keep under ~400 words.
- Structure: Summary → Top drivers → What to do first → Closed-loop note.
"""


@dataclass
class FactsPack:
    score_combined: float
    severity: str
    score_confirmed: float
    score_possible: float
    vector: str
    explanation_summary: str
    model_version: str
    contributions: list[dict[str, Any]] = field(default_factory=list)
    counterfactuals: list[dict[str, Any]] = field(default_factory=list)
    attributions: list[str] = field(default_factory=list)
    open_recommendation_titles: list[str] = field(default_factory=list)
    broker_statuses: list[dict[str, str]] = field(default_factory=list)
    identifier_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_combined": self.score_combined,
            "severity": self.severity,
            "score_confirmed": self.score_confirmed,
            "score_possible": self.score_possible,
            "vector": self.vector,
            "explanation_summary": self.explanation_summary,
            "model_version": self.model_version,
            "contributions": self.contributions,
            "counterfactuals": self.counterfactuals,
            "attributions": self.attributions,
            "open_recommendation_titles": self.open_recommendation_titles,
            "broker_statuses": self.broker_statuses,
            "identifier_types": self.identifier_types,
        }

    def redacted_for_llm(self) -> dict[str, Any]:
        safe_contributions = []
        for c in self.contributions:
            safe_c = {
                "title": c.get("title"),
                "source": c.get("source"),
                "severity": c.get("severity"),
                "layer": c.get("layer"),
                "tags": c.get("tags"),
                "weighted_score": c.get("weighted_score"),
                "raw_score": c.get("raw_score")
            }
            safe_contributions.append({k: v for k, v in safe_c.items() if v is not None})
            
        return {
            "score_combined": self.score_combined,
            "severity": self.severity,
            "score_confirmed": self.score_confirmed,
            "score_possible": self.score_possible,
            "vector": self.vector,
            "explanation_summary": self.explanation_summary,
            "model_version": self.model_version,
            "contributions": safe_contributions,
            "counterfactuals": self.counterfactuals,
            "attributions": self.attributions,
            "open_recommendation_titles": self.open_recommendation_titles,
            "broker_statuses": self.broker_statuses,
            "identifier_types": self.identifier_types,
        }


def build_deterministic_narrative(facts: FactsPack) -> str:
    lines: list[str] = []
    lines.append(
        f"## Personal exposure briefing\n\n"
        f"Your current PDSS is **{facts.score_combined:.1f}** ({facts.severity}). "
        f"Confirmed track: {facts.score_confirmed:.1f}; possible track: {facts.score_possible:.1f}. "
        f"Model: `{facts.model_version}`."
    )
    if facts.explanation_summary:
        lines.append(f"\n{facts.explanation_summary}")

    if facts.contributions:
        lines.append("\n### Top drivers")
        for c in facts.contributions[:5]:
            title = c.get("title") or c.get("finding_id")
            src = c.get("source", "?")
            w = c.get("weighted_score", c.get("raw_score", "?"))
            lines.append(f"- [{src}] {title} (weighted contribution ≈ {w})")

    if facts.counterfactuals:
        lines.append("\n### What-if (estimated impact of fixing top items)")
        for cf in facts.counterfactuals[:3]:
            lines.append(f"- {cf.get('narrative') or cf}")

    if facts.open_recommendation_titles:
        lines.append("\n### Suggested next steps (from your plan)")
        for t in facts.open_recommendation_titles[:5]:
            lines.append(f"- {t}")

    if facts.broker_statuses:
        lines.append("\n### Remediation state (sample)")
        for b in facts.broker_statuses[:5]:
            lines.append(f"- {b.get('broker_id')}: {b.get('status')}")

    if facts.attributions:
        lines.append("\n### Data attributions")
        for a in facts.attributions:
            lines.append(f"- {a}")

    lines.append(
        "\n### Closed loop\n"
        "After you change passwords, complete freezes, or finish Green broker opt-outs, "
        "run a rescan and recompute PDSS so the score reflects real-world change. "
        "This briefing uses only stored DigiZafe facts — no external invention."
    )
    return "\n".join(lines)


def user_prompt_from_facts(facts: FactsPack) -> str:
    import json
    return (
        "Write a grounded personal digital exposure briefing from FACTS only.\n\n"
        f"FACTS:\n{json.dumps(facts.redacted_for_llm(), default=str)[:12000]}\n"
    )
