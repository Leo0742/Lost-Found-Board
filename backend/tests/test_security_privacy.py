from datetime import UTC, datetime, timedelta

from app.core.auth import generate_session_id
from app.models.auth_session import WebAuthSession


def _create_session_cookie(db_session_factory, telegram_user_id: int | None = None):
    with db_session_factory() as db:
        session = WebAuthSession(
            id=generate_session_id(),
            telegram_user_id=telegram_user_id,
            telegram_username="tester" if telegram_user_id else None,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db.add(session)
        db.commit()
        return {"lfb_session": session.id}


def _create_item(client, **overrides):
    suffix = f"{overrides.get('telegram_user_id', 0)}-{overrides.get('status', 'lost')}-{overrides.get('title', 'Wallet')}"
    payload = {
        "title": f"Wallet {suffix}",
        "description": f"Black leather wallet {suffix}",
        "category": "Accessories",
        "location": "Library",
        "status": "lost",
        "contact_name": "Alice",
        "telegram_username": "@alice",
        "telegram_user_id": 1001,
    }
    payload.update(overrides)
    response = client.post("/api/items", json=payload)
    assert response.status_code == 201
    return response.json()


def test_public_item_response_hides_private_fields(client):
    item = _create_item(client)

    list_response = client.get("/api/items")
    assert list_response.status_code == 200
    body = list_response.json()[0]
    for forbidden in [
        "contact_name",
        "telegram_username",
        "telegram_user_id",
        "owner_telegram_user_id",
        "owner_telegram_username",
        "owner_display_name",
    ]:
        assert forbidden not in body

    detail_response = client.get(f"/api/items/{item['id']}")
    assert detail_response.status_code == 200
    for forbidden in ["contact_name", "telegram_username", "telegram_user_id", "owner_telegram_user_id"]:
        assert forbidden not in detail_response.json()


def test_me_endpoint_requires_session_and_returns_owner_data(client, db_session_factory):
    _create_item(client, telegram_user_id=111)
    no_auth = client.get("/api/items/me")
    assert no_auth.status_code == 401

    cookies = _create_session_cookie(db_session_factory, telegram_user_id=111)
    me = client.get("/api/items/me", cookies=cookies)
    assert me.status_code == 200
    assert me.json()[0]["contact_name"] == "Alice"


def test_public_detail_blocks_non_public_records(client, db_session_factory):
    item = _create_item(client, telegram_user_id=222)

    cookies = _create_session_cookie(db_session_factory, telegram_user_id=222)
    deleted = client.post(f"/api/items/{item['id']}/delete", json={}, cookies=cookies)
    assert deleted.status_code == 200

    public_detail = client.get(f"/api/items/{item['id']}")
    assert public_detail.status_code == 404

    owner_detail = client.get(f"/api/items/{item['id']}", cookies=cookies)
    assert owner_detail.status_code == 200


def test_claim_contact_shared_only_after_approval(client, db_session_factory):
    source = _create_item(client, telegram_user_id=100, status="lost")
    target = _create_item(client, telegram_user_id=200, status="found")

    requester_cookies = _create_session_cookie(db_session_factory, telegram_user_id=100)
    owner_cookies = _create_session_cookie(db_session_factory, telegram_user_id=200)

    create_claim_resp = client.post(
        "/api/items/claim-requests",
        json={"source_item_id": source["id"], "target_item_id": target["id"]},
        cookies=requester_cookies,
    )
    assert create_claim_resp.status_code == 200
    claim_id = create_claim_resp.json()["id"]

    claim_before = client.get("/api/items/claim-requests", params={"direction": "outgoing"}, cookies=requester_cookies)
    assert claim_before.status_code == 200
    assert claim_before.json()[0]["shared_source_contact"] is None

    approved = client.post(f"/api/items/claim-requests/{claim_id}/approve", json={}, cookies=owner_cookies)
    assert approved.status_code == 200

    claim_after = client.get("/api/items/claim-requests", params={"direction": "outgoing"}, cookies=requester_cookies)
    assert claim_after.json()[0]["shared_source_contact"]


def test_public_matches_do_not_expose_owner_ids(client):
    base = _create_item(client, telegram_user_id=501, status="lost", title="Airpods case", description="Lost white case")
    _create_item(client, telegram_user_id=502, status="found", title="Found apple airpods case", description="found white case near library")

    response = client.get(f"/api/items/matches/{base['id']}")
    assert response.status_code == 200
    if response.json():
        assert "telegram_user_id" not in response.json()[0]
