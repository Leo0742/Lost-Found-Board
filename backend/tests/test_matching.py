from app.models.item import Item, ItemStatus
from app.services.matching import score_match, score_match_detailed


def make_item(**kwargs):
    defaults = {
        "id": 1,
        "title": "Black wallet",
        "description": "Leather wallet with student ID",
        "category": "Accessories",
        "location": "Science Building",
        "status": ItemStatus.LOST,
        "contact_name": "John",
    }
    defaults.update(kwargs)
    return Item(**defaults)


def test_match_score_prefers_opposite_status_with_overlap():
    lost = make_item()
    found = make_item(
        id=2,
        status=ItemStatus.FOUND,
        title="Found dark card holder",
        description="Cardholder with student card near dormitory A",
        location="Near dorm A entrance",
    )

    details = score_match_detailed(lost, found)

    assert details.score >= 5.0
    assert details.confidence in {"medium", "high"}
    assert any("semantic" in r for r in details.reasons)


def test_match_score_zero_for_same_status():
    item_a = make_item(status=ItemStatus.LOST)
    item_b = make_item(id=3, status=ItemStatus.LOST)

    assert score_match(item_a, item_b) == 0


def test_typos_and_synonyms_still_match():
    source = make_item(
        title="Airpods csae",
        description="Lost apple earbuds charging case",
        category="Electronics",
        location="Dormitory A",
    )
    candidate = make_item(
        id=9,
        status=ItemStatus.FOUND,
        title="apple earphones case",
        description="Found airpods case near dorm A",
        category="Electronics",
        location="near dorm a",
    )

    details = score_match_detailed(source, candidate)

    assert details.score >= 6.0
    assert "matching object type" in details.reasons
