from datetime import UTC, datetime, timedelta

from app.core.auth import generate_csrf_token, generate_session_id
from app.core.config import get_settings
from app.models.auth_session import WebAuthSession
from app.services.readiness import check_readiness


def _create_session(db_session_factory, *, telegram_user_id: int | None = None) -> tuple[dict, dict, str]:
    with db_session_factory() as db:
        session = WebAuthSession(
            id=generate_session_id(),
            csrf_token=generate_csrf_token(),
            telegram_user_id=telegram_user_id,
            telegram_username=f"u{telegram_user_id}" if telegram_user_id else None,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db.add(session)
        db.commit()
        return {"lfb_session": session.id}, {"X-CSRF-Token": session.csrf_token}, session.id


def _create_item(client, telegram_user_id: int, status: str = "lost") -> dict:
    response = client.post(
        "/api/items",
        json={
            "title": f"Item {telegram_user_id}-{status}",
            "description": "Test description",
            "category": "Other",
            "location": "Library",
            "status": status,
            "contact_name": "Alice",
            "telegram_user_id": telegram_user_id,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_session_user_cannot_mutate_other_owner_item(client, db_session_factory):
    item = _create_item(client, telegram_user_id=100)
    cookies, headers, _ = _create_session(db_session_factory, telegram_user_id=200)

    resp = client.post(f"/api/items/{item['id']}/resolve", json={}, cookies=cookies, headers=headers)
    assert resp.status_code == 403


def test_payload_spoofed_telegram_user_id_does_not_grant_claim_access(client, db_session_factory):
    source = _create_item(client, telegram_user_id=100, status="lost")
    target = _create_item(client, telegram_user_id=200, status="found")
    cookies, headers, _ = _create_session(db_session_factory, telegram_user_id=999)

    create = client.post(
        "/api/items/claim-requests",
        json={"source_item_id": source["id"], "target_item_id": target["id"], "requester_telegram_user_id": 100},
        cookies=cookies,
        headers=headers,
    )
    assert create.status_code == 403


def test_internal_endpoints_require_token(client):
    denied = client.post("/api/items/internal/1/resolve", json={"telegram_user_id": 1})
    assert denied.status_code == 403


def test_public_cannot_patch_item(client):
    item = _create_item(client, telegram_user_id=300)
    denied = client.patch(f"/api/items/{item['id']}", json={"title": "Hacked"})
    assert denied.status_code == 403


def test_owner_can_patch_only_own_item(client, db_session_factory):
    item = _create_item(client, telegram_user_id=400)
    cookies, headers, _ = _create_session(db_session_factory, telegram_user_id=400)
    ok = client.patch(f"/api/items/{item['id']}", json={"title": "Updated title"}, cookies=cookies, headers=headers)
    assert ok.status_code == 200
    assert ok.json()["title"] == "Updated title"


def test_auth_transitions_rotate_session_id(client, db_session_factory):
    cookies, headers, session_id = _create_session(db_session_factory, telegram_user_id=123)

    unlink = client.post("/api/auth/unlink", cookies=cookies, headers=headers)
    assert unlink.status_code == 204
    assert "set-cookie" in unlink.headers
    unlink_cookie = unlink.headers["set-cookie"]
    assert "lfb_session=" in unlink_cookie
    assert session_id not in unlink_cookie

    new_session = unlink_cookie.split("lfb_session=")[1].split(";")[0]
    with db_session_factory() as db:
        assert db.get(WebAuthSession, session_id) is None
        assert db.get(WebAuthSession, new_session) is not None


def test_non_dev_readiness_fails_with_default_internal_token(client, db_session_factory, monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("STRICT_INTERNAL_TOKEN", "true")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "change-me-internal-token")
    get_settings.cache_clear()

    with db_session_factory() as db:
        report = check_readiness(db)
    assert report.config_ok is False
    assert report.ready is False

    get_settings.cache_clear()
