from app.models.item import Item, ItemStatus
from app.services.matching import score_match


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
        title="Found black wallet",
        description="Found leather wallet near student center",
        location="Science Building lobby",
    )

    score = score_match(lost, found)

    assert score >= 3.0


def test_match_score_zero_for_same_status():
    item_a = make_item(status=ItemStatus.LOST)
    item_b = make_item(id=3, status=ItemStatus.LOST)

    assert score_match(item_a, item_b) == 0
