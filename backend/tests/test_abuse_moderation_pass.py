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

    stats = client.get("/api/items/admin/moderation-stats", cookies=cookies, headers=headers)
    assert stats.status_code == 200
    assert "recent_abuse_blocks_24h" in stats.json()

    signals = client.get("/api/items/admin/moderation-signals", params={"item_ids": [item["id"]]}, cookies=cookies, headers=headers)
    assert signals.status_code == 200
    assert signals.json()[0]["item_id"] == item["id"]
