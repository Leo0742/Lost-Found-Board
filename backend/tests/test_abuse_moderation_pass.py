from datetime import UTC, datetime, timedelta

from app.core.auth import generate_csrf_token, generate_session_id
from app.core.config import get_settings
from app.models.auth_session import WebAuthSession


def _create_web_session(db_session_factory, *, telegram_user_id: int | None = None, telegram_username: str | None = None):
    with db_session_factory() as db:
        session = WebAuthSession(
            id=generate_session_id(),
            csrf_token=generate_csrf_token(),
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            expires_at=datetime.now(UTC) + timedelta(days=5),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id, session.csrf_token


def _payload(title: str, user_id: int = 101):
    return {
        "title": title,
        "description": f"Description for {title}",
        "category": "Accessories",
        "location": "Library",
        "status": "lost",
        "contact_name": "Alice",
        "telegram_user_id": user_id,
    }


def test_flag_duplicate_and_rate_limit(client, db_session_factory, monkeypatch):
    monkeypatch.setenv("FLAG_RATE_LIMIT_WINDOW_MINUTES", "30")
    monkeypatch.setenv("FLAG_RATE_LIMIT_MAX", "2")
    get_settings.cache_clear()

    created = client.post("/api/items", json=_payload("Flag base"))
    item_id = created.json()["id"]

    session_id, csrf = _create_web_session(db_session_factory, telegram_user_id=222)
    cookies = {"lfb_session": session_id}
    headers = {"X-CSRF-Token": csrf}

    first = client.post(f"/api/items/{item_id}/flag", json={"reason": "spam content"}, cookies=cookies, headers=headers)
    assert first.status_code == 200

    duplicate = client.post(f"/api/items/{item_id}/flag", json={"reason": "spam   content"}, cookies=cookies, headers=headers)
    assert duplicate.status_code == 409

    another = client.post(f"/api/items/{item_id}/flag", json={"reason": "other reason"}, cookies=cookies, headers=headers)
    assert another.status_code == 429


def test_claim_rate_limit(client, db_session_factory, monkeypatch):
    monkeypatch.setenv("CLAIM_RATE_LIMIT_WINDOW_MINUTES", "30")
    monkeypatch.setenv("CLAIM_RATE_LIMIT_MAX", "1")
    get_settings.cache_clear()

    source = client.post("/api/items", json=_payload("Source", user_id=700)).json()
    target = client.post("/api/items", json={**_payload("Target", user_id=701), "status": "found"}).json()

    session_id, csrf = _create_web_session(db_session_factory, telegram_user_id=700)
    cookies = {"lfb_session": session_id}
    headers = {"X-CSRF-Token": csrf}

    ok = client.post("/api/items/claim-requests", json={"source_item_id": source["id"], "target_item_id": target["id"]}, cookies=cookies, headers=headers)
    assert ok.status_code == 200

    limited = client.post("/api/items/claim-requests", json={"source_item_id": source["id"], "target_item_id": target["id"]}, cookies=cookies, headers=headers)
    assert limited.status_code == 429


def test_admin_audit_and_moderation_stats_filters(client, db_session_factory, monkeypatch):
    monkeypatch.setenv("ADMIN_TELEGRAM_USER_IDS", "3001")
    get_settings.cache_clear()

    session_id, csrf = _create_web_session(db_session_factory, telegram_user_id=3001)
    cookies = {"lfb_session": session_id}
    headers = {"X-CSRF-Token": csrf}

    item = client.post("/api/items", json=_payload("Moderation stats", user_id=902)).json()
    client.post(f"/api/items/{item['id']}/flag", json={"reason": "suspicious"}, cookies=cookies, headers=headers)

    audit = client.get(
        "/api/items/admin/audit-events",
        params={"event_type": "item_flagged", "item_id": item["id"], "limit": 10, "offset": 0},
        cookies=cookies,
        headers=headers,
    )
    assert audit.status_code == 200
    assert all(row["event_type"] == "item_flagged" for row in audit.json())
    assert audit.json()[0]["summary"]

    stats = client.get("/api/items/admin/moderation-stats", cookies=cookies, headers=headers)
    assert stats.status_code == 200
    assert "recent_abuse_blocks_24h" in stats.json()

    signals = client.get("/api/items/admin/moderation-signals", params={"item_ids": [item["id"]]}, cookies=cookies, headers=headers)
    assert signals.status_code == 200
    assert signals.json()[0]["item_id"] == item["id"]
    assert "duplicate_flags_24h" in signals.json()[0]
    assert "blocked_events_24h" in signals.json()[0]


def test_admin_bulk_actions_and_observability(client, db_session_factory, monkeypatch):
    monkeypatch.setenv("ADMIN_TELEGRAM_USER_IDS", "3001")
    get_settings.cache_clear()

    session_id, csrf = _create_web_session(db_session_factory, telegram_user_id=3001)
    cookies = {"lfb_session": session_id}
    headers = {"X-CSRF-Token": csrf}

    one = client.post("/api/items", json=_payload("Bulk one", user_id=990)).json()
    two = client.post("/api/items", json=_payload("Bulk two", user_id=991)).json()

    bulk_mod = client.post(
        "/api/items/admin/items/bulk-moderate",
        json={"item_ids": [one["id"], two["id"]], "action": "approve"},
        cookies=cookies,
        headers=headers,
    )
    assert bulk_mod.status_code == 200
    assert bulk_mod.json()["succeeded"] == 2

    bulk_verify = client.post(
        "/api/items/admin/items/bulk-verify",
        json={"item_ids": [one["id"], two["id"]], "is_verified": True},
        cookies=cookies,
        headers=headers,
    )
    assert bulk_verify.status_code == 200
    assert bulk_verify.json()["failed"] == 0

    queue_summary = client.get("/api/items/admin/queue-summary", cookies=cookies, headers=headers)
    assert queue_summary.status_code == 200
    assert "pending_total" in queue_summary.json()
    assert "stale_pending_48h" in queue_summary.json()

    observability = client.get("/api/items/admin/observability", cookies=cookies, headers=headers)
    assert observability.status_code == 200
    payload = observability.json()
    assert "duplicate_flags_24h" in payload
    assert "cleanup" in payload
    assert "maintenance_status" in payload["cleanup"]


def test_bulk_action_isolates_unexpected_item_errors(client, db_session_factory, monkeypatch):
    monkeypatch.setenv("ADMIN_TELEGRAM_USER_IDS", "3001")
    get_settings.cache_clear()

    session_id, csrf = _create_web_session(db_session_factory, telegram_user_id=3001)
    cookies = {"lfb_session": session_id}
    headers = {"X-CSRF-Token": csrf}

    one = client.post("/api/items", json=_payload("Bulk isolate one", user_id=1111)).json()
    two = client.post("/api/items", json=_payload("Bulk isolate two", user_id=1112)).json()

    from app.services.item_service import ItemService

    original = ItemService.moderate_item

    def flaky(self, item, action, moderator, reason=None):
        if item.id == two["id"]:
            raise RuntimeError("unexpected")
        return original(self, item, action, moderator, reason)

    monkeypatch.setattr(ItemService, "moderate_item", flaky)
    response = client.post(
        "/api/items/admin/items/bulk-moderate",
        json={"item_ids": [one["id"], two["id"]], "action": "approve"},
        cookies=cookies,
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["succeeded"] == 1
    assert payload["failed"] == 1
    failed = [row for row in payload["results"] if not row["success"]]
    assert failed and failed[0]["detail"] == "Unexpected server error"


def test_admin_items_supports_suspicious_only_filter(client, db_session_factory, monkeypatch):
    monkeypatch.setenv("ADMIN_TELEGRAM_USER_IDS", "3001")
    get_settings.cache_clear()

    session_id, csrf = _create_web_session(db_session_factory, telegram_user_id=3001)
    cookies = {"lfb_session": session_id}
    headers = {"X-CSRF-Token": csrf}

    flagged = client.post("/api/items", json=_payload("Suspicious item", user_id=1200)).json()
    normal = client.post("/api/items", json=_payload("Normal item", user_id=1201)).json()
    client.post(
        f"/api/items/admin/items/{flagged['id']}/moderate",
        json={"action": "flag", "reason": "flagged by moderator"},
        cookies=cookies,
        headers=headers,
    )

    response = client.get("/api/items/admin/items", params={"suspicious_only": True}, cookies=cookies, headers=headers)
    assert response.status_code == 200
    item_ids = {row["id"] for row in response.json()}
    assert flagged["id"] in item_ids
    assert normal["id"] not in item_ids
