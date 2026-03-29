from datetime import datetime, UTC

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.item import Item, ItemLifecycle, ItemStatus
from app.schemas.item import ItemCreate, ItemUpdate, MatchResult
from app.services.matching import score_match_detailed


class ItemService:
    def __init__(self, db: Session):
        self.db = db

    def create_item(self, payload: ItemCreate) -> Item:
        item = Item(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_items(
        self,
        status: ItemStatus | None = None,
        category: str | None = None,
        q: str | None = None,
        lifecycle: ItemLifecycle | None = ItemLifecycle.ACTIVE,
    ) -> list[Item]:
        query: Select[tuple[Item]] = select(Item)
        if lifecycle:
            query = query.where(Item.lifecycle == lifecycle)
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

    def list_my_items(self, telegram_user_id: int) -> list[Item]:
        query: Select[tuple[Item]] = (
            select(Item).where(Item.telegram_user_id == telegram_user_id).order_by(Item.created_at.desc())
        )
        return list(self.db.scalars(query).all())

    def is_owner(self, item: Item, telegram_user_id: int) -> bool:
        return bool(item.telegram_user_id and item.telegram_user_id == telegram_user_id)

    def mark_resolved(self, item: Item) -> Item:
        item.lifecycle = ItemLifecycle.RESOLVED
        item.resolved_at = datetime.now(UTC)
        item.deleted_at = None
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def reopen(self, item: Item) -> Item:
        item.lifecycle = ItemLifecycle.ACTIVE
        item.resolved_at = None
        item.deleted_at = None
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_item(self, item: Item) -> Item:
        item.lifecycle = ItemLifecycle.DELETED
        item.deleted_at = datetime.now(UTC)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def matches_for_item(self, item: Item, limit: int = 5) -> list[MatchResult]:
        if item.lifecycle != ItemLifecycle.ACTIVE:
            return []

        candidates = self.list_items(
            status=ItemStatus.FOUND if item.status == ItemStatus.LOST else ItemStatus.LOST,
            lifecycle=ItemLifecycle.ACTIVE,
        )
        scored = []
        for candidate in candidates:
            if candidate.id == item.id:
                continue
            details = score_match_detailed(item, candidate)
            if details.score >= 3.5:
                scored.append((candidate, details))

        scored.sort(key=lambda pair: pair[1].score, reverse=True)
        return [
            MatchResult(
                id=c.id,
                title=c.title,
                status=c.status,
                category=c.category,
                location=c.location,
                relevance_score=d.score,
                confidence=d.confidence,
                reasons=d.reasons,
                telegram_user_id=c.telegram_user_id,
            )
            for c, d in scored[:limit]
        ]
