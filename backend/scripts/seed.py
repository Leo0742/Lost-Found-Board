from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.item import Item, ItemStatus

SAMPLE_ITEMS = [
    {
        "title": "Blue Jansport Backpack",
        "description": "Lost near library entrance with notebooks and charger.",
        "category": "Bags",
        "location": "Main Library",
        "status": ItemStatus.LOST,
        "contact_name": "Ariana M",
        "telegram_username": "ariana_student",
    },
    {
        "title": "Silver Water Bottle",
        "description": "Found in Engineering Hall room 204 after class.",
        "category": "Accessories",
        "location": "Engineering Hall",
        "status": ItemStatus.FOUND,
        "contact_name": "Lab Assistant",
        "telegram_username": "eng_lab",
    },
    {
        "title": "AirPods Case",
        "description": "Found white AirPods case by cafeteria tables.",
        "category": "Electronics",
        "location": "Student Cafeteria",
        "status": ItemStatus.FOUND,
        "contact_name": "Campus Help Desk",
        "telegram_username": "campushelp",
    },
]


def run() -> None:
    with SessionLocal() as db:
        db.execute(delete(Item))
        for payload in SAMPLE_ITEMS:
            db.add(Item(**payload))
        db.commit()


if __name__ == "__main__":
    run()
