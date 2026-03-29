from app.services.catalog import infer_category
from app.services.search_utils import rank_items


class DummyItem:
    def __init__(self, title: str, description: str, location: str, category: str):
        self.title = title
        self.description = description
        self.location = location
        self.category = category


def test_category_inference_examples():
    assert infer_category("iPhone 13 Pro").category == "Phones"
    assert infer_category("student id card").category == "ID Cards"
    assert infer_category("usb flash drive").category == "USB / Storage"
    assert infer_category("black backpack").category == "Backpacks"
    assert infer_category("dog").category == "Other"


def test_fuzzy_search_typo_and_partial():
    items = [
        DummyItem("Black wallet", "leather card holder", "Dormitory A", "Wallets"),
        DummyItem("AirPods case", "white charging case", "Library", "Headphones"),
    ]
    ranked = rank_items("walet", items, limit=5)
    assert ranked
    assert ranked[0].item.title == "Black wallet"

    ranked2 = rank_items("air pod", items, limit=5)
    assert ranked2
    assert ranked2[0].item.title == "AirPods case"
