"""Goal and asset-opportunity fit helpers."""

from __future__ import annotations

import re

from kdaa.models import AssetRecord, StrategicGoal


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9+\-]{2,}", text.lower())
        if token not in {"the", "and", "for", "with", "from", "into", "that", "this"}
    }


def goal_alignment_score(
    assets: list[AssetRecord],
    goals: list[StrategicGoal],
    opportunity_text: str,
) -> float:
    if not goals:
        return 0.55
    asset_text = " ".join(
        [
            *(asset.label for asset in assets),
            *(asset.bounded_claim for asset in assets),
            *(" ".join(asset.concept_tags) for asset in assets),
        ]
    )
    target_tokens = _tokens(asset_text + " " + opportunity_text)
    weighted_scores: list[tuple[float, float]] = []
    for goal in goals:
        goal_tokens = _tokens(goal.label + " " + goal.description + " " + " ".join(goal.keywords))
        if not goal_tokens:
            continue
        overlap = len(target_tokens & goal_tokens) / len(goal_tokens)
        weighted_scores.append((min(1.0, overlap * 2.5), goal.weight))
    if not weighted_scores:
        return 0.50
    return sum(score * weight for score, weight in weighted_scores) / sum(
        weight for _, weight in weighted_scores
    )
