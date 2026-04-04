import io

from app.models.audit_event import AuditEvent
from app.services import matching


def _create_item(client, **overrides):
    payload = {
        "title": "Wallet alpha",
        "description": "Black leather wallet",
        "category": "Accessories",
        "location": "Library",
        "status": "lost",
        "contact_name": "Alice",
        "telegram_user_id": 123,
    }
    payload.update(overrides)
    response = client.post("/api/items", json=payload)
    assert response.status_code == 201
    return response.json()


def test_ready_endpoint_reports_degraded_semantic_but_ready(client, monkeypatch):
    monkeypatch.setattr(matching, "_EMBEDDING_AVAILABLE", False)
    monkeypatch.setattr(matching, "_SEMANTIC_DETAIL", "model unavailable")
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["matching_state"] == "degraded"


def test_audit_events_created_for_item_and_claim(client, db_session_factory):
    source = _create_item(client, title="Lost keys", status="lost", telegram_user_id=100)
    target = _create_item(client, title="Found keys", status="found", telegram_user_id=200)

    claim = client.post(
        "/api/items/claim-requests",
        json={"source_item_id": source["id"], "target_item_id": target["id"], "requester_telegram_user_id": 100},
    )
    assert claim.status_code == 200

    with db_session_factory() as db:
        events = db.query(AuditEvent).all()
        event_types = {e.event_type for e in events}

    assert "item_created" in event_types
    assert "claim_created" in event_types


def test_image_upload_flow_uses_temp_path(client):
    files = {"image": ("proof.jpg", io.BytesIO(b"\xff\xd8\xff\xe0" + b"x" * 10), "image/jpeg")}
    upload = client.post("/api/items/upload-image", files=files, headers={"X-Internal-Token": "change-me-internal-token"})
    assert upload.status_code == 200
    image_path = upload.json()["image_path"]
    assert image_path.startswith("tmp/")

    created = _create_item(client, image_path=image_path, image_filename="proof.jpg", image_mime_type="image/jpeg")
    assert created["image_path"]
    assert not created["image_path"].startswith("tmp/")
