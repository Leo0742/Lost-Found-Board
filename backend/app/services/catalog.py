from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

CATEGORY_CATALOG: list[str] = [
    "Electronics",
    "Phones",
    "Laptops",
    "Tablets",
    "Headphones",
    "Chargers & Cables",
    "Smart Watches",
    "USB / Storage",
    "Documents",
    "ID Cards",
    "Bank Cards",
    "Keys",
    "Bags",
    "Backpacks",
    "Wallets",
    "Accessories",
    "Glasses",
    "Clothing",
    "Shoes",
    "Jewelry",
    "Books & Notebooks",
    "Bottles / Cups",
    "Umbrellas",
    "Sports Items",
    "Cosmetics",
    "Toys",
    "Other",
]

@dataclass
class CategorySuggestion:
    category: str
    confidence: float
    reasons: list[str]


_CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "Phones": {"phone", "iphone", "android", "samsung", "pixel", "smartphone", "mobile"},
    "Laptops": {"laptop", "macbook", "notebook", "thinkpad", "chromebook"},
    "Tablets": {"tablet", "ipad", "galaxy tab", "surface"},
    "Headphones": {"airpods", "earbud", "headphone", "headset", "buds"},
    "Chargers & Cables": {"charger", "cable", "usb c", "lightning", "adapter", "power bank"},
    "Smart Watches": {"watch", "smartwatch", "apple watch", "fitbit", "band"},
    "USB / Storage": {"usb", "flash drive", "pendrive", "ssd", "hdd", "memory card", "sd card"},
    "Documents": {"passport", "document", "visa", "certificate", "paper"},
    "ID Cards": {"id", "student id", "badge", "campus card", "license"},
    "Bank Cards": {"debit", "credit", "bank card", "mastercard", "visa card", "atm"},
    "Keys": {"key", "keys", "keychain", "car key"},
    "Bags": {"bag", "tote", "purse", "handbag", "duffel"},
    "Backpacks": {"backpack", "rucksack", "school bag"},
    "Wallets": {"wallet", "cardholder", "card holder", "money clip"},
    "Glasses": {"glasses", "spectacles", "sunglasses"},
    "Clothing": {"jacket", "hoodie", "shirt", "coat", "sweater", "uniform"},
    "Shoes": {"shoe", "sneaker", "boot", "slipper", "sandals"},
    "Jewelry": {"ring", "necklace", "bracelet", "earring"},
    "Books & Notebooks": {"book", "notebook", "textbook", "journal"},
    "Bottles / Cups": {"bottle", "cup", "mug", "flask", "thermos"},
    "Umbrellas": {"umbrella"},
    "Sports Items": {"ball", "racket", "sports", "helmet", "gloves"},
    "Cosmetics": {"makeup", "cosmetic", "lipstick", "perfume", "skincare"},
    "Toys": {"toy", "lego", "doll", "game"},
    "Electronics": {"electronic", "device", "gadget", "camera", "mouse", "keyboard"},
    "Accessories": {"accessory", "case", "cover", "strap"},
}

_TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
})


def normalize_text(value: str) -> str:
    lowered = value.lower().translate(_TRANSLIT)
    lowered = unicodedata.normalize("NFKD", lowered)
    lowered = "".join(ch for ch in lowered if not unicodedata.combining(ch))
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def infer_category(title: str) -> CategorySuggestion:
    normalized = normalize_text(title)
    if not normalized:
        return CategorySuggestion(category="Other", confidence=0.0, reasons=["empty title"])

    best_category = "Other"
    best_score = 0.0
    reasons: list[str] = []
    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = 0.0
        local_reasons: list[str] = []
        for keyword in keywords:
            n_kw = normalize_text(keyword)
            if n_kw and n_kw in normalized:
                score += 1.0
                local_reasons.append(keyword)
        if score > best_score:
            best_score = score
            best_category = category
            reasons = local_reasons

    confidence = min(0.95, best_score / 2.0) if best_score > 0 else 0.0
    if confidence < 0.35:
        return CategorySuggestion(category="Other", confidence=confidence, reasons=["low keyword confidence"])
    return CategorySuggestion(category=best_category, confidence=confidence, reasons=reasons[:3])
