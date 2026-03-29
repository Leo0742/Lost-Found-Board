from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.item import Item, ItemStatus
from app.schemas.item import ItemCreate, ItemUpdate, MatchResult
from app.services.matching import score_match


class ItemService:
    def __init__(self, db: Session):
        self.db = db

    def create_item(self, payload: ItemCreate) -> Item:
        item = Item(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_items(self, status: ItemStatus | None = None, category: str | None = None, q: str | None = None) -> list[Item]:
        query: Select[tuple[Item]] = select(Item)
        if status:
            query = query.where(Item.status == status)
        if category:
            query = query.where(Item.category.ilike(category))
        if q:
            like_q = f"%{q}%"
            query = query.where(Item.title.ilike(like_q) | Item.description.ilike(like_q) | Item.location.ilike(like_q))
        query = query.order_by(Item.created_at.desc())
        return list(self.db.scalars(query).all())

    def get_item(self, item_id: int) -> Item | None:
        return self.db.get(Item, item_id)

    def update_item(self, item: Item, payload: ItemUpdate) -> Item:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_item(self, item: Item) -> None:
        self.db.delete(item)
        self.db.commit()

    def matches_for_item(self, item: Item, limit: int = 5) -> list[MatchResult]:
        candidates = self.list_items(status=ItemStatus.FOUND if item.status == ItemStatus.LOST else ItemStatus.LOST)
        scored = []
        for candidate in candidates:
            if candidate.id == item.id:
                continue
            score = score_match(item, candidate)
            if score > 1.0:
                scored.append((candidate, score))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [
            MatchResult(
                id=c.id,
                title=c.title,
                status=c.status,
                category=c.category,
                location=c.location,
                relevance_score=s,
            )
            for c, s in scored[:limit]
        ]
