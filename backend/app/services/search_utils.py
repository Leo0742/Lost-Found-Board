from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from app.models.item import Item
from app.services.catalog import normalize_text


@dataclass
class SmartSearchResult:
    item: Item
    score: float
    reasons: list[str]


def rank_items(query: str, items: list[Item], limit: int = 8) -> list[SmartSearchResult]:
    normalized_query = normalize_text(query)
    query_tokens = set(normalized_query.split())
    ranked: list[SmartSearchResult] = []

    for item in items:
        hay_title = normalize_text(item.title)
        hay_desc = normalize_text(item.description)
        hay_loc = normalize_text(item.location)
        hay_cat = normalize_text(item.category)
        joined = f"{hay_title} {hay_desc} {hay_loc} {hay_cat}".strip()

        title_ratio = fuzz.WRatio(normalized_query, hay_title)
        joined_ratio = fuzz.WRatio(normalized_query, joined)
        partial_ratio = fuzz.partial_ratio(normalized_query, joined)

        token_hits = len(query_tokens & set(joined.split()))
        token_score = min(100, token_hits * 20)

        score = 0.45 * title_ratio + 0.30 * joined_ratio + 0.15 * partial_ratio + 0.10 * token_score
        reasons: list[str] = []
        if title_ratio >= 80:
            reasons.append("strong title similarity")
        if token_hits > 0:
            reasons.append(f"{token_hits} token overlap")
        if fuzz.WRatio(normalized_query, hay_loc) >= 75:
            reasons.append("location similarity")
        if fuzz.WRatio(normalized_query, hay_cat) >= 75:
            reasons.append("category similarity")
        if normalized_query in joined:
            reasons.append("direct partial text match")

        if score >= 45:
            ranked.append(SmartSearchResult(item=item, score=round(score, 1), reasons=reasons[:3]))

    ranked.sort(key=lambda x: x.score, reverse=True)
    return ranked[:limit]
