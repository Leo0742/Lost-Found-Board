from datetime import UTC, datetime, timedelta

from app.core.auth import generate_csrf_token, generate_session_id
from app.core.config import get_settings
from app.models.auth_session import WebAuthSession
from app.models.audit_event import AuditEvent
from app.services import media


def _reset_settings_cache():
    get_settings.cache_clear()


def _create_web_session(db_session_factory, *, telegram_user_id: int | None = None, telegram_username: str | None = None, csrf: str | None = None):
    with db_session_factory() as db:
        session = WebAuthSession(
            id=generate_session_id(),
            csrf_token=csrf,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            expires_at=datetime.now(UTC) + timedelta(days=5),
        )
        db.add(session)
        db.commit()
        return session.id


def _payload(title: str = "Lost wallet"):
    return {
        "title": title,
        "description": f"Description for {title}",
        "category": "Accessories",
        "location": "Library",
        "status": "lost",
        "contact_name": "Alice",
        "telegram_user_id": 100,
    }


def test_csrf_enforced_for_cookie_session_mutations(client, db_session_factory):
    session_id = _create_web_session(db_session_factory, telegram_user_id=100, csrf=generate_csrf_token())
    cookies = {"lfb_session": session_id}

    denied = client.post("/api/items", json=_payload("Need CSRF"), cookies=cookies)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "CSRF validation failed"

    with db_session_factory() as db:
        session = db.get(WebAuthSession, session_id)
        token = session.csrf_token

    allowed = client.post("/api/items", json=_payload("Has CSRF"), cookies=cookies, headers={"X-CSRF-Token": token})
    assert allowed.status_code == 201


def test_internal_mutation_flow_still_works_without_csrf_cookie(client):
    created = client.post("/api/items", json=_payload("Internal flow"))
    assert created.status_code == 201


def test_admin_bootstrap_username_is_moderator_only(client, db_session_factory, monkeypatch):
    monkeypatch.setenv("ADMIN_TELEGRAM_USER_IDS", "2001")
    monkeypatch.setenv("ADMIN_TELEGRAM_USERNAMES", "bootstrap_user")
    monkeypatch.setenv("ADMIN_USERNAME_BOOTSTRAP_ENABLED", "true")
    get_settings.cache_clear()

    session_id = _create_web_session(db_session_factory, telegram_user_id=9999, telegram_username="bootstrap_user", csrf=generate_csrf_token())
    response = client.get("/api/auth/me", cookies={"lfb_session": session_id})
    assert response.status_code == 200
    assert response.json()["role"] == "moderator"
    _reset_settings_cache()


def test_temp_media_cleanup_removes_orphans_after_failed_create(client, db_session_factory):
    upload = client.post(
        "/api/items/upload-image",
        files={"image": ("test.jpg", b"\xff\xd8\xff" + b"x" * 20, "image/jpeg")},
        headers={"X-Internal-Token": "change-me-internal-token"},
    )
    assert upload.status_code == 200
    tmp_path = upload.json()["image_path"]
    root = media.media_root()
    assert (root / tmp_path).exists()

    # duplicate payload causes anti-spam rejection and should cleanup uploaded temp file
    ok = client.post("/api/items", json=_payload("dup title"))
    assert ok.status_code == 201
    rejected = client.post("/api/items", json={**_payload("dup title"), "image_path": tmp_path})
    assert rejected.status_code == 400
    assert not (root / tmp_path).exists()


def test_admin_audit_events_endpoint(client, db_session_factory, monkeypatch):
    monkeypatch.setenv("ADMIN_TELEGRAM_USER_IDS", "3001")
    get_settings.cache_clear()
    session_id = _create_web_session(db_session_factory, telegram_user_id=3001, csrf=generate_csrf_token())

    with db_session_factory() as db:
        db.add(AuditEvent(event_type="item_moderated", actor_telegram_user_id=3001, item_id=10, details={"action": "approve"}))
        db.commit()

    with db_session_factory() as db:
        token = db.get(WebAuthSession, session_id).csrf_token

    response = client.get("/api/items/admin/audit-events", params={"event_type": "item_moderated"}, cookies={"lfb_session": session_id}, headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    events = response.json()
    assert events
    assert events[0]["event_type"] == "item_moderated"
    _reset_settings_cache()
