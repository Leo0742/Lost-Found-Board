import re
from collections import Counter

from app.models.item import Item


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def _tokens(text: str) -> set[str]:
    return {tok.lower() for tok in TOKEN_RE.findall(text)}


def score_match(source: Item, candidate: Item) -> float:
    if source.status == candidate.status:
        return 0

    score = 1.0

    if source.category.lower() == candidate.category.lower():
        score += 2.0

    source_terms = _tokens(f"{source.title} {source.description}")
    candidate_terms = _tokens(f"{candidate.title} {candidate.description}")
    common = source_terms.intersection(candidate_terms)
    score += min(len(common) * 0.5, 3.0)

    source_location_terms = Counter(_tokens(source.location))
    candidate_location_terms = Counter(_tokens(candidate.location))
    shared_location = sum((source_location_terms & candidate_location_terms).values())
    score += min(shared_location * 0.7, 2.0)

    return round(score, 2)
