import logging
import math
import os
import re
from difflib import SequenceMatcher
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - optional dependency fallback
    fuzz = None

try:
    from fastembed import TextEmbedding
except Exception:  # pragma: no cover - optional dependency fallback
    TextEmbedding = None

from app.core.config import get_settings
from app.models.item import Item


class SemanticState(str, Enum):
    ENABLED = "enabled"
    DEGRADED = "degraded"
    DISABLED = "disabled"


@dataclass(slots=True)
class SemanticRuntimeStatus:
    state: SemanticState
    detail: str


logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z0-9а-я]+", flags=re.IGNORECASE)
PUNCT_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)
SPACE_RE = re.compile(r"\s+")

ALIASES = {
    "dormitory": "dorm",
    "hostel": "dorm",
    "общежитие": "dorm",
    "obshezhitie": "dorm",
    "wallet": "wallet",
    "cardholder": "wallet",
    "card holder": "wallet",
    "purse": "wallet",
    "кошелек": "wallet",
    "наушники": "headphones",
    "earbuds": "headphones",
    "earphones": "headphones",
    "airpods": "airpods",
    "charger": "charger",
    "charging cable": "charger",
    "adapter": "charger",
    "dark": "black",
    "library": "library",
    "lib": "library",
    "cafeteria": "canteen",
    "canteen": "canteen",
}

LOCATION_ALIASES = {
    "dormitory a": "dorm a",
    "dorm a entrance": "dorm a entrance",
    "dormitory a entrance": "dorm a entrance",
    "общежитие а": "dorm a",
    "near dorm a": "dorm a",
}

OBJECT_TYPES = {
    "wallet": {"wallet", "card", "cardholder", "purse", "кошелек"},
    "headphones": {"headphones", "earbuds", "earphones", "airpods", "наушники"},
    "charger": {"charger", "adapter", "cable", "charging"},
    "bag": {"bag", "backpack", "рюкзак", "pouch"},
}

COLORS = {"black", "white", "blue", "red", "green", "silver", "gray", "grey", "pink", "yellow"}
BRANDS = {"apple", "samsung", "xiaomi", "sony", "jbl", "lenovo", "hp", "asus", "dell"}

CATEGORY_FAMILY = {
    "electronics": "electronics",
    "accessories": "personal",
    "bags": "personal",
    "documents": "documents",
    "keys": "keys",
    "other": "other",
}

TRANSLIT = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "i",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "ch",
        "ш": "sh",
        "щ": "sh",
        "ы": "y",
        "э": "e",
        "ю": "u",
        "я": "ya",
    }
)


@dataclass(slots=True)
class ProcessedItem:
    combined: str
    normalized_title: str
    normalized_description: str
    normalized_location: str
    normalized_category: str
    tokens: set[str]
    location_tokens: set[str]
    object_types: set[str]
    colors: set[str]
    brands: set[str]
    model_tokens: set[str]
    category_family: str
    distinctive: set[str]


@dataclass(slots=True)
class MatchDetails:
    score: float
    confidence: str
    reasons: list[str]


def _normalize_text(text: str, for_location: bool = False) -> str:
    normalized = SPACE_RE.sub(" ", PUNCT_RE.sub(" ", text.lower())).strip()
    normalized = normalized.translate(TRANSLIT)
    mapping = LOCATION_ALIASES if for_location else ALIASES
    for src, tgt in mapping.items():
        normalized = normalized.replace(src, tgt)
    normalized = SPACE_RE.sub(" ", normalized).strip()
    return normalized


def _tokens(text: str) -> set[str]:
    return {tok for tok in TOKEN_RE.findall(text.lower()) if len(tok) > 1}


def _extract_object_types(tokens: set[str]) -> set[str]:
    extracted = set()
    for obj_type, aliases in OBJECT_TYPES.items():
        if tokens.intersection(aliases):
            extracted.add(obj_type)
    return extracted


def _extract_models(tokens: set[str]) -> set[str]:
    return {tok for tok in tokens if any(ch.isdigit() for ch in tok) and len(tok) >= 3}


def _prep(item: Item) -> ProcessedItem:
    title = _normalize_text(item.title)
    description = _normalize_text(item.description)
    location = _normalize_text(item.location, for_location=True)
    category = _normalize_text(item.category)

    tokens = _tokens(f"{title} {description} {category}")
    location_tokens = _tokens(location)

    object_types = _extract_object_types(tokens)
    colors = {token for token in tokens if token in COLORS}
    brands = {token for token in tokens if token in BRANDS}
    model_tokens = _extract_models(tokens)
    category_family = CATEGORY_FAMILY.get(category, "other")

    stop_words = {"with", "near", "the", "and", "for", "from", "found", "lost"}
    distinctive = {t for t in tokens if t not in stop_words and len(t) >= 4}

    combined = f"{title} | {category} | {description} | {location}"
    return ProcessedItem(
        combined=combined,
        normalized_title=title,
        normalized_description=description,
        normalized_location=location,
        normalized_category=category,
        tokens=tokens,
        location_tokens=location_tokens,
        object_types=object_types,
        colors=colors,
        brands=brands,
        model_tokens=model_tokens,
        category_family=category_family,
        distinctive=distinctive,
    )


@lru_cache(maxsize=1)
def _encoder():
    if TextEmbedding is None:
        raise RuntimeError("fastembed is not available")
    settings = get_settings()
    return TextEmbedding(model_name=settings.embedding_model_name)


_EMBEDDING_AVAILABLE: bool | None = None
_SEMANTIC_DETAIL: str = "semantic warmup not attempted"


def semantic_runtime_status() -> SemanticRuntimeStatus:
    settings = get_settings()
    if not settings.semantic_matching_enabled:
        return SemanticRuntimeStatus(state=SemanticState.DISABLED, detail="disabled by configuration")
    if _EMBEDDING_AVAILABLE is True:
        return SemanticRuntimeStatus(state=SemanticState.ENABLED, detail="semantic model loaded")
    if _EMBEDDING_AVAILABLE is False:
        return SemanticRuntimeStatus(state=SemanticState.DEGRADED, detail=_SEMANTIC_DETAIL)
    return SemanticRuntimeStatus(state=SemanticState.DEGRADED, detail=_SEMANTIC_DETAIL)


def warmup_embedding_model() -> bool:
    global _EMBEDDING_AVAILABLE, _SEMANTIC_DETAIL
    settings = get_settings()
    if not settings.semantic_matching_enabled:
        _EMBEDDING_AVAILABLE = False
        _SEMANTIC_DETAIL = "semantic disabled by configuration"
        logger.info("Semantic matching disabled by configuration; rule-based matching only.")
        return False

    if _EMBEDDING_AVAILABLE is False:
        return False

    try:
        _encoder()
        _embed_text("embedding warmup text")
        _EMBEDDING_AVAILABLE = True
        _SEMANTIC_DETAIL = "semantic model loaded"
        logger.info("Semantic matching state: enabled.")
        return True
    except Exception as exc:
        _EMBEDDING_AVAILABLE = False
        _SEMANTIC_DETAIL = f"model warmup failed: {exc}"
        logger.warning("Semantic matching state: degraded (%s).", exc)
        return False


def _semantic_available() -> bool:
    settings = get_settings()
    if not settings.semantic_matching_enabled:
        return False
    if _EMBEDDING_AVAILABLE is None and settings.embedding_warmup_on_startup:
        return warmup_embedding_model()
    return _EMBEDDING_AVAILABLE is True


@lru_cache(maxsize=4096)
def _embed_text(text: str) -> tuple[float, ...]:
    vec = list(_encoder().embed([text]))[0]
    norm = math.sqrt(sum(float(x) * float(x) for x in vec)) or 1.0
    return tuple(float(x) / norm for x in vec)


def _cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def _fuzzy_ratio(a: str, b: str) -> float:
    if fuzz is not None:
        return fuzz.token_set_ratio(a, b) / 100.0
    return SequenceMatcher(None, a, b).ratio()


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a.intersection(b)) / len(a.union(b))


def score_match(source: Item, candidate: Item) -> float:
    return score_match_detailed(source, candidate).score


def score_match_detailed(source: Item, candidate: Item) -> MatchDetails:
    if source.status == candidate.status:
        return MatchDetails(score=0.0, confidence="low", reasons=["same status, skipped"])

    src = _prep(source)
    cand = _prep(candidate)

    reasons: list[str] = ["opposite status"]

    category_score = 1.0 if src.normalized_category == cand.normalized_category else 0.0
    if category_score:
        reasons.append("same category")
    elif src.category_family == cand.category_family and src.category_family != "other":
        category_score = 0.65
        reasons.append("compatible category family")

    keyword_overlap = _jaccard(src.tokens, cand.tokens)
    if keyword_overlap > 0.15:
        reasons.append("keyword overlap")

    fuzzy_title = _fuzzy_ratio(src.normalized_title, cand.normalized_title)
    fuzzy_location = _fuzzy_ratio(src.normalized_location, cand.normalized_location)
    fuzzy_object = _fuzzy_ratio(" ".join(sorted(src.object_types)), " ".join(sorted(cand.object_types)))

    feature_object = _jaccard(src.object_types, cand.object_types)
    feature_brand = _jaccard(src.brands, cand.brands)
    feature_color = _jaccard(src.colors, cand.colors)
    feature_model = _jaccard(src.model_tokens, cand.model_tokens)
    distinctive_overlap = _jaccard(src.distinctive, cand.distinctive)

    if feature_object > 0:
        reasons.append("matching object type")
    if fuzzy_location > 0.72:
        reasons.append("similar location")
    if feature_brand > 0 or feature_model > 0:
        reasons.append("brand/model signal")

    semantic_score = 0.0
    if _semantic_available():
        try:
            semantic_score = (1.0 + _cosine(_embed_text(src.combined), _embed_text(cand.combined))) / 2.0
            if semantic_score > 0.70:
                reasons.append("semantic similarity detected")
        except Exception as exc:
            logger.warning("Semantic scoring failed; using fallback scoring only: %s", exc)
            global _EMBEDDING_AVAILABLE, _SEMANTIC_DETAIL
            _EMBEDDING_AVAILABLE = False
            _SEMANTIC_DETAIL = f"runtime scoring failure: {exc}"

    contradiction_penalty = 0.0
    if src.colors and cand.colors and not src.colors.intersection(cand.colors):
        contradiction_penalty += 0.08
    if src.object_types and cand.object_types and not src.object_types.intersection(cand.object_types):
        contradiction_penalty += 0.12

    hybrid = (
        0.12 * category_score
        + 0.14 * keyword_overlap
        + 0.12 * fuzzy_title
        + 0.10 * fuzzy_location
        + 0.08 * fuzzy_object
        + 0.20 * semantic_score
        + 0.12 * feature_object
        + 0.05 * feature_brand
        + 0.03 * feature_color
        + 0.02 * feature_model
        + 0.02 * distinctive_overlap
    )

    rerank_boost = 0.0
    if semantic_score > 0.74 and (feature_object > 0 or fuzzy_object > 0.8):
        rerank_boost += 0.08
        reasons.append("rerank boost: semantic + object alignment")
    if fuzzy_location > 0.85:
        rerank_boost += 0.04

    final = max(0.0, min(1.0, hybrid + rerank_boost - contradiction_penalty))
    score = round(final * 10, 2)

    confidence = "low"
    if final >= 0.75:
        confidence = "high"
    elif final >= 0.50:
        confidence = "medium"

    if not reasons:
        reasons = ["weak match"]

    return MatchDetails(score=score, confidence=confidence, reasons=sorted(set(reasons)))
