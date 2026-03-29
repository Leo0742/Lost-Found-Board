from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Select, select, func
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from app.models.item import Item, ItemLifecycle, ItemStatus, ModerationStatus
from app.models.claim import Claim, ClaimStatus
from app.schemas.item import ItemCreate, ItemUpdate, MatchResult
from app.core.config import get_settings
from app.services.matching import score_match_detailed


class ItemService:
    def __init__(self, db: Session):
        self.db = db

    def create_item(self, payload: ItemCreate) -> Item:
        self._enforce_anti_spam(payload)
        item = Item(**payload.model_dump())
        if not item.owner_telegram_user_id and item.telegram_user_id:
            item.owner_telegram_user_id = item.telegram_user_id
        if not item.owner_telegram_username and item.telegram_username:
            item.owner_telegram_username = item.telegram_username
        if not item.owner_display_name:
            item.owner_display_name = item.contact_name
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def _enforce_anti_spam(self, payload: ItemCreate) -> None:
        settings = get_settings()
        now = datetime.now(UTC)
        window_start = now.timestamp() - (settings.create_rate_limit_window_minutes * 60)
        user_id = payload.telegram_user_id

        if user_id:
            recent_count = self.db.scalar(
                select(func.count(Item.id)).where(
                    Item.telegram_user_id == user_id,
                    Item.created_at >= datetime.fromtimestamp(window_start, UTC),
                )
            )
            if recent_count and recent_count >= settings.create_rate_limit_max_items:
                raise HTTPException(status_code=429, detail="Too many reports in a short period. Please try later.")

        duplicate = self.db.scalar(
            select(Item).where(
                Item.title.ilike(payload.title.strip()),
                Item.description.ilike(payload.description.strip()),
                Item.contact_name.ilike(payload.contact_name.strip()),
                Item.created_at >= datetime.fromtimestamp(now.timestamp() - 24 * 3600, UTC),
            )
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="Duplicate report detected. Please update details instead.")

        combined = f"{payload.title} {payload.description}".strip().lower()
        if len(set(ch for ch in combined if ch.isalnum())) < 4:
            raise HTTPException(status_code=400, detail="Report text looks suspiciously low quality.")

    @staticmethod
    def image_url(image_path: str | None) -> str | None:
        if not image_path:
            return None
        settings = get_settings()
        return f"{settings.media_url_prefix}/{image_path}"

    def save_image(self, image: UploadFile) -> tuple[str, str, str]:
        allowed = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
        mime = image.content_type or ""
        if mime not in allowed:
            raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WEBP images are allowed.")

        raw = image.file.read()
        settings = get_settings()
        if not raw:
            raise HTTPException(status_code=400, detail="Uploaded image is empty.")
        if len(raw) > settings.media_max_bytes:
            raise HTTPException(status_code=400, detail=f"Image is too large (max {settings.media_max_bytes // (1024*1024)}MB).")

        suffix = allowed[mime]
        safe_name = f"{uuid4().hex}{suffix}"
        media_root = Path(settings.media_root)
        media_root.mkdir(parents=True, exist_ok=True)
        target = media_root / safe_name
        target.write_bytes(raw)
        original_name = image.filename or safe_name
        return safe_name, original_name[:255], mime

    def list_items(
        self,
        status: ItemStatus | None = None,
        category: str | None = None,
        q: str | None = None,
        lifecycle: ItemLifecycle | None = ItemLifecycle.ACTIVE,
        moderation_status: ModerationStatus | None = ModerationStatus.APPROVED,
    ) -> list[Item]:
        query: Select[tuple[Item]] = select(Item)
        if lifecycle:
            query = query.where(Item.lifecycle == lifecycle)
        if moderation_status:
            query = query.where(Item.moderation_status == moderation_status)
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
            select(Item)
            .where((Item.owner_telegram_user_id == telegram_user_id) | (Item.telegram_user_id == telegram_user_id))
            .order_by(Item.created_at.desc())
        )
        return list(self.db.scalars(query).all())

    def is_owner(self, item: Item, telegram_user_id: int) -> bool:
        if item.owner_telegram_user_id:
            return item.owner_telegram_user_id == telegram_user_id
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

    def moderate_item(self, item: Item, action: str, moderator: str, reason: str | None = None) -> Item:
        mapping = {
            "approve": ModerationStatus.APPROVED,
            "reject": ModerationStatus.REJECTED,
            "flag": ModerationStatus.FLAGGED,
            "unflag": ModerationStatus.APPROVED,
        }
        item.moderation_status = mapping[action]
        item.moderation_reason = reason
        item.moderated_by = moderator
        item.moderated_at = datetime.now(UTC)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def verify_item(self, item: Item, is_verified: bool) -> Item:
        item.is_verified = is_verified
        item.verified_at = datetime.now(UTC) if is_verified else None
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def admin_lifecycle_action(self, item: Item, action: str) -> Item:
        if action == "resolve":
            return self.mark_resolved(item)
        if action == "reopen":
            return self.reopen(item)
        return self.delete_item(item)

    def flag_item(self, item: Item, reason: str) -> Item:
        item.moderation_status = ModerationStatus.FLAGGED
        item.moderation_reason = reason
        item.moderated_at = datetime.now(UTC)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def create_claim(
        self,
        source_item: Item,
        target_item: Item,
        requester_telegram_user_id: int | None,
        requester_name: str | None,
        claim_message: str | None,
    ) -> Claim:
        existing = self.db.scalar(
            select(Claim).where(
                Claim.source_item_id == source_item.id,
                Claim.target_item_id == target_item.id,
                Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED]),
            )
        )
        if existing:
            raise HTTPException(status_code=400, detail="A claim already exists for this match.")

        claim = Claim(
            source_item_id=source_item.id,
            target_item_id=target_item.id,
            requester_telegram_user_id=requester_telegram_user_id or source_item.telegram_user_id,
            owner_telegram_user_id=target_item.owner_telegram_user_id or target_item.telegram_user_id,
            requester_name=requester_name,
            claim_message=claim_message,
            status=ClaimStatus.PENDING,
        )
        self.db.add(claim)
        self.db.commit()
        self.db.refresh(claim)
        return claim

    def get_claim(self, claim_id: int) -> Claim | None:
        return self.db.get(Claim, claim_id)

    def list_claims(self, telegram_user_id: int, direction: str = "all") -> list[Claim]:
        query = select(Claim)
        if direction == "incoming":
            query = query.where(Claim.owner_telegram_user_id == telegram_user_id)
        elif direction == "outgoing":
            query = query.where(Claim.requester_telegram_user_id == telegram_user_id)
        else:
            query = query.where(
                (Claim.owner_telegram_user_id == telegram_user_id) | (Claim.requester_telegram_user_id == telegram_user_id)
            )
        return list(self.db.scalars(query.order_by(Claim.created_at.desc())).all())

    def update_claim_status(self, claim: Claim, status: ClaimStatus, note: str | None = None) -> Claim:
        allowed_transitions = {
            ClaimStatus.PENDING: {ClaimStatus.APPROVED, ClaimStatus.REJECTED, ClaimStatus.CANCELLED},
            ClaimStatus.APPROVED: {ClaimStatus.COMPLETED, ClaimStatus.NOT_MATCH, ClaimStatus.CANCELLED},
            ClaimStatus.REJECTED: set(),
            ClaimStatus.CANCELLED: set(),
            ClaimStatus.COMPLETED: set(),
            ClaimStatus.NOT_MATCH: set(),
        }
        if claim.status == status:
            return claim
        if status not in allowed_transitions.get(claim.status, set()):
            raise HTTPException(
                status_code=409,
                detail=f"Invalid claim transition from '{claim.status.value}' to '{status.value}'",
            )

        claim.status = status
        if note:
            claim.handoff_note = note
        if status == ClaimStatus.COMPLETED:
            claim.resolved_by_claim = True
        self.db.add(claim)
        self.db.commit()
        self.db.refresh(claim)
        return claim

    def claim_read(self, claim: Claim, viewer_telegram_user_id: int | None = None):
        source = self.get_item(claim.source_item_id)
        target = self.get_item(claim.target_item_id)
        shared_source_contact = None
        shared_target_contact = None
        if claim.status in {ClaimStatus.APPROVED, ClaimStatus.COMPLETED} and viewer_telegram_user_id:
            if viewer_telegram_user_id in {claim.requester_telegram_user_id, claim.owner_telegram_user_id}:
                if source:
                    shared_source_contact = source.telegram_username or source.contact_name
                if target:
                    shared_target_contact = target.telegram_username or target.contact_name
        from app.schemas.item import ClaimRead

        return ClaimRead(
            id=claim.id,
            source_item_id=claim.source_item_id,
            target_item_id=claim.target_item_id,
            requester_telegram_user_id=claim.requester_telegram_user_id,
            owner_telegram_user_id=claim.owner_telegram_user_id,
            requester_name=claim.requester_name,
            claim_message=claim.claim_message,
            status=claim.status,
            handoff_note=claim.handoff_note,
            resolved_by_claim=claim.resolved_by_claim,
            created_at=claim.created_at,
            updated_at=claim.updated_at,
            source_item_title=source.title if source else None,
            target_item_title=target.title if target else None,
            shared_source_contact=shared_source_contact,
            shared_target_contact=shared_target_contact,
        )

    def matches_for_item(self, item: Item, limit: int = 5) -> list[MatchResult]:
        if item.lifecycle != ItemLifecycle.ACTIVE or item.moderation_status != ModerationStatus.APPROVED:
            return []

        candidates = self.list_items(
            status=ItemStatus.FOUND if item.status == ItemStatus.LOST else ItemStatus.LOST,
            lifecycle=ItemLifecycle.ACTIVE,
            moderation_status=ModerationStatus.APPROVED,
        )
        scored = []
        for candidate in candidates:
            if candidate.id == item.id:
                continue
            blocked_pair = self.db.scalar(
                select(Claim).where(
                    (
                        (Claim.source_item_id == item.id) & (Claim.target_item_id == candidate.id)
                    )
                    | (
                        (Claim.source_item_id == candidate.id) & (Claim.target_item_id == item.id)
                    ),
                    Claim.status.in_([ClaimStatus.NOT_MATCH, ClaimStatus.COMPLETED]),
                )
            )
            if blocked_pair:
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
                image_path=c.image_path,
            )
            for c, d in scored[:limit]
        ]
