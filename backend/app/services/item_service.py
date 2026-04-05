from datetime import datetime, UTC, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from app.models.item import Item, ItemLifecycle, ItemStatus, ModerationStatus
from app.models.claim import Claim, ClaimStatus
from app.models.audit_event import AuditEvent
from app.models.anti_abuse_event import AntiAbuseEvent
from app.schemas.item import InternalMatchResult, ItemCreate, MatchResult
from app.core.config import get_settings
from app.services.matching import score_match_detailed
from app.services.catalog import CATEGORY_CATALOG, infer_category
from app.services.search_utils import rank_items
from app.services.audit import log_event
from app.services.anti_abuse import AbuseAction, has_recent_duplicate, normalize_reason, record_signal
from app.services.media import finalize_uploaded_image, is_tmp_path, remove_media_file
from app.models.user_profile import UserProfile
from app.services.profile_contacts import exposed_contact_summary


class ItemService:
    def __init__(self, db: Session):
        self.db = db

    def create_item(self, payload: ItemCreate) -> Item:
        cleanup_path = payload.image_path if is_tmp_path(payload.image_path) else None
        try:
            self._enforce_anti_spam(payload)
            normalized = payload.model_dump()
            normalized["image_path"] = finalize_uploaded_image(normalized.get("image_path"))
            item = Item(**normalized)
            if not item.owner_telegram_user_id and item.telegram_user_id:
                item.owner_telegram_user_id = item.telegram_user_id
            if not item.owner_telegram_username and item.telegram_username:
                item.owner_telegram_username = item.telegram_username
            if not item.owner_display_name:
                item.owner_display_name = item.contact_name
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            log_event(self.db, "item_created", actor_telegram_user_id=item.owner_telegram_user_id or item.telegram_user_id, item_id=item.id, details={"status": item.status.value, "has_image": bool(item.image_path)})
            self.db.commit()
            return item
        except Exception:
            if cleanup_path:
                remove_media_file(cleanup_path)
            raise

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
        safe_name = f"tmp_{uuid4().hex}{suffix}"
        media_root = Path(settings.media_root)
        temp_root = media_root / "tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        target = temp_root / safe_name
        target.write_bytes(raw)
        original_name = image.filename or safe_name
        return f"tmp/{safe_name}", original_name[:255], mime

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

    def list_items_admin(
        self,
        *,
        status: ItemStatus | None = None,
        lifecycle: ItemLifecycle | None = None,
        moderation_status: ModerationStatus | None = None,
        category: str | None = None,
        is_verified: bool | None = None,
        actor_telegram_user_id: int | None = None,
        q: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 200,
        offset: int = 0,
        suspicious_only: bool = False,
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
        if is_verified is not None:
            query = query.where(Item.is_verified.is_(is_verified))
        if actor_telegram_user_id is not None:
            query = query.where(
                (Item.owner_telegram_user_id == actor_telegram_user_id)
                | (Item.telegram_user_id == actor_telegram_user_id)
            )
        if created_from:
            query = query.where(Item.created_at >= created_from)
        if created_to:
            query = query.where(Item.created_at <= created_to)
        if q:
            like_q = f"%{q}%"
            query = query.where(
                Item.title.ilike(like_q)
                | Item.description.ilike(like_q)
                | Item.location.ilike(like_q)
                | Item.contact_name.ilike(like_q)
                | Item.owner_telegram_username.ilike(like_q)
                | Item.telegram_username.ilike(like_q)
            )
        if suspicious_only:
            since_24h = datetime.now(UTC) - timedelta(hours=24)
            flag_spike = (
                select(func.count(AuditEvent.id))
                .where(
                    AuditEvent.event_type == "item_flagged",
                    AuditEvent.item_id == Item.id,
                    AuditEvent.created_at >= since_24h,
                )
                .scalar_subquery()
            )
            duplicate_pressure = (
                select(func.count(AntiAbuseEvent.id))
                .where(
                    AntiAbuseEvent.action == AbuseAction.FLAG_DUPLICATE.value,
                    AntiAbuseEvent.item_id == Item.id,
                    AntiAbuseEvent.created_at >= since_24h,
                )
                .scalar_subquery()
            )
            blocked_pressure = (
                select(func.count(AntiAbuseEvent.id))
                .where(
                    AntiAbuseEvent.item_id == Item.id,
                    AntiAbuseEvent.blocked.is_(True),
                    AntiAbuseEvent.created_at >= since_24h,
                )
                .scalar_subquery()
            )
            claim_spike = (
                select(func.count(Claim.id))
                .where(
                    or_(Claim.source_item_id == Item.id, Claim.target_item_id == Item.id),
                    Claim.created_at >= since_24h,
                )
                .scalar_subquery()
            )
            query = query.where(
                or_(
                    Item.moderation_status == ModerationStatus.FLAGGED,
                    flag_spike >= 3,
                    duplicate_pressure >= 2,
                    blocked_pressure >= 2,
                    claim_spike >= 3,
                )
            )

        sort_fields = {
            "created_at": Item.created_at,
            "updated_at": Item.updated_at,
            "moderated_at": Item.moderated_at,
            "id": Item.id,
        }
        col = sort_fields.get(sort_by, Item.created_at)
        primary_sort = col.asc() if sort_order == "asc" else col.desc()
        tie_breaker = Item.id.asc() if sort_order == "asc" else Item.id.desc()
        query = query.order_by(primary_sort, tie_breaker)
        query = query.limit(limit).offset(offset)
        return list(self.db.scalars(query).all())

    def list_categories(self) -> list[str]:
        return CATEGORY_CATALOG

    def suggest_category(self, title: str) -> dict:
        suggestion = infer_category(title)
        return {
            "category": suggestion.category,
            "confidence": round(suggestion.confidence, 2),
            "reasons": suggestion.reasons,
        }

    def smart_search(self, query: str, limit: int = 8) -> list[dict]:
        base_items = self.list_items(
            lifecycle=ItemLifecycle.ACTIVE,
            moderation_status=ModerationStatus.APPROVED,
        )
        ranked = rank_items(query, base_items, limit=limit)
        return [
            {
                "item": row.item,
                "relevance_score": row.score,
                "reasons": row.reasons,
            }
            for row in ranked
        ]

    def get_item(self, item_id: int) -> Item | None:
        return self.db.get(Item, item_id)

    def update_item(self, item: Item, data: dict, *, actor_telegram_user_id: int | None = None) -> Item:
        old_image = item.image_path
        cleanup_path = data.get("image_path") if is_tmp_path(data.get("image_path")) else None
        try:
            if "image_path" in data:
                data["image_path"] = finalize_uploaded_image(data.get("image_path"))
            for key, value in data.items():
                setattr(item, key, value)
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            if old_image and old_image != item.image_path:
                remove_media_file(old_image)
            log_event(
                self.db,
                "item_updated",
                actor_telegram_user_id=actor_telegram_user_id or item.owner_telegram_user_id or item.telegram_user_id,
                item_id=item.id,
                details={"fields": sorted(data.keys())},
            )
            self.db.commit()
            return item
        except Exception:
            if cleanup_path:
                remove_media_file(cleanup_path)
            raise

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
        log_event(self.db, "item_resolved", actor_telegram_user_id=item.owner_telegram_user_id or item.telegram_user_id, item_id=item.id)
        self.db.commit()
        return item

    def reopen(self, item: Item) -> Item:
        item.lifecycle = ItemLifecycle.ACTIVE
        item.resolved_at = None
        item.deleted_at = None
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        log_event(self.db, "item_reopened", actor_telegram_user_id=item.owner_telegram_user_id or item.telegram_user_id, item_id=item.id)
        self.db.commit()
        return item

    def delete_item(self, item: Item) -> Item:
        item.lifecycle = ItemLifecycle.DELETED
        item.deleted_at = datetime.now(UTC)
        if item.image_path:
            remove_media_file(item.image_path)
            item.image_path = None
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        log_event(self.db, "item_deleted", actor_telegram_user_id=item.owner_telegram_user_id or item.telegram_user_id, item_id=item.id)
        self.db.commit()
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
        log_event(self.db, "item_moderated", item_id=item.id, details={"action": action, "moderator": moderator, "reason": reason})
        self.db.commit()
        return item

    def verify_item(self, item: Item, is_verified: bool) -> Item:
        item.is_verified = is_verified
        item.verified_at = datetime.now(UTC) if is_verified else None
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        log_event(self.db, "item_verification_changed", item_id=item.id, details={"is_verified": is_verified})
        self.db.commit()
        return item

    def admin_lifecycle_action(self, item: Item, action: str) -> Item:
        if action == "resolve":
            return self.mark_resolved(item)
        if action == "reopen":
            return self.reopen(item)
        return self.delete_item(item)

    def flag_item(self, item: Item, reason: str, *, actor_telegram_user_id: int | None = None, session_id: str | None = None, ip_hash: str | None = None) -> Item:
        normalized_reason = normalize_reason(reason)
        fingerprint = normalized_reason
        if has_recent_duplicate(
            self.db,
            action=AbuseAction.FLAG_SUBMISSION.value,
            actor_telegram_user_id=actor_telegram_user_id,
            session_id=session_id,
            ip_hash=ip_hash,
            fingerprint=fingerprint,
            item_id=item.id,
            within_hours=24,
        ):
            record_signal(
                self.db,
                action=AbuseAction.FLAG_DUPLICATE.value,
                actor_telegram_user_id=actor_telegram_user_id,
                session_id=session_id,
                ip_hash=ip_hash,
                fingerprint=fingerprint,
                item_id=item.id,
            )
            self.db.commit()
            raise HTTPException(status_code=409, detail="You already submitted the same flag recently.")

        item.moderation_status = ModerationStatus.FLAGGED
        item.moderation_reason = reason
        item.moderated_at = datetime.now(UTC)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        record_signal(
            self.db,
            action=AbuseAction.FLAG_SUBMISSION.value,
            actor_telegram_user_id=actor_telegram_user_id,
            session_id=session_id,
            ip_hash=ip_hash,
            fingerprint=fingerprint,
            item_id=item.id,
        )
        self.db.commit()
        log_event(
            self.db,
            "item_flagged",
            actor_telegram_user_id=actor_telegram_user_id,
            item_id=item.id,
            details={"reason": reason, "normalized_reason": normalized_reason, "session_id": bool(session_id), "ip_tracked": bool(ip_hash)},
        )
        self.db.commit()
        return item

    def create_claim(
        self,
        source_item: Item,
        target_item: Item,
        requester_telegram_user_id: int | None,
        requester_name: str | None,
        claim_message: str | None,
        *,
        session_id: str | None = None,
        ip_hash: str | None = None,
    ) -> Claim:
        fingerprint = f"{min(source_item.id, target_item.id)}:{max(source_item.id, target_item.id)}"
        if has_recent_duplicate(
            self.db,
            action=AbuseAction.CLAIM_SUBMISSION.value,
            actor_telegram_user_id=requester_telegram_user_id,
            session_id=session_id,
            ip_hash=ip_hash,
            fingerprint=fingerprint,
            item_id=source_item.id,
            within_hours=24,
        ):
            record_signal(
                self.db,
                action=AbuseAction.CLAIM_DUPLICATE.value,
                actor_telegram_user_id=requester_telegram_user_id,
                session_id=session_id,
                ip_hash=ip_hash,
                fingerprint=fingerprint,
                item_id=source_item.id,
            )
            self.db.commit()
            raise HTTPException(status_code=409, detail="You already created a similar claim recently.")

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
        record_signal(
            self.db,
            action=AbuseAction.CLAIM_SUBMISSION.value,
            actor_telegram_user_id=claim.requester_telegram_user_id,
            session_id=session_id,
            ip_hash=ip_hash,
            fingerprint=fingerprint,
            item_id=source_item.id,
        )
        self.db.commit()
        log_event(
            self.db,
            "claim_created",
            actor_telegram_user_id=claim.requester_telegram_user_id,
            item_id=source_item.id,
            claim_id=claim.id,
            details={"target_item_id": target_item.id},
        )
        self.db.commit()
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
        log_event(
            self.db,
            "claim_status_changed",
            actor_telegram_user_id=claim.requester_telegram_user_id,
            claim_id=claim.id,
            details={"status": status.value},
        )
        self.db.commit()
        return claim

    def claim_read(self, claim: Claim, viewer_telegram_user_id: int | None = None):
        source = self.get_item(claim.source_item_id)
        target = self.get_item(claim.target_item_id)
        shared_source_contact = None
        shared_target_contact = None
        if claim.status in {ClaimStatus.APPROVED, ClaimStatus.COMPLETED} and viewer_telegram_user_id:
            if viewer_telegram_user_id in {claim.requester_telegram_user_id, claim.owner_telegram_user_id}:
                if source:
                    source_profile = None
                    if source.owner_telegram_user_id:
                        source_profile = self.db.scalar(select(UserProfile).where(UserProfile.telegram_user_id == source.owner_telegram_user_id))
                    shared_source_contact = (
                        exposed_contact_summary(source_profile) if source_profile else None
                    ) or source.telegram_username or source.contact_name
                if target:
                    target_profile = None
                    if target.owner_telegram_user_id:
                        target_profile = self.db.scalar(select(UserProfile).where(UserProfile.telegram_user_id == target.owner_telegram_user_id))
                    shared_target_contact = (
                        exposed_contact_summary(target_profile) if target_profile else None
                    ) or target.telegram_username or target.contact_name
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

    def matches_for_item(self, item: Item, limit: int = 5, include_telegram_user_id: bool = False) -> list[MatchResult]:
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
        result_cls = InternalMatchResult if include_telegram_user_id else MatchResult
        return [
            result_cls(
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
