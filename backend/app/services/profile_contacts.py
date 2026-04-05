import json
from typing import Any

from app.models.user_profile import UserProfile

CONTACT_VISIBILITY_ALL = "all"
CONTACT_VISIBILITY_ONE = "one"


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def parse_custom_contact_methods(raw_json: str | None) -> list[dict[str, str]]:
    if not raw_json:
        return []
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []

    parsed: list[dict[str, str]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        method_id = _normalize_text(str(row.get("id") or ""))
        name = _normalize_text(str(row.get("name") or ""))
        value = _normalize_text(str(row.get("value") or ""))
        if not method_id or not name or not value:
            continue
        parsed.append({"id": method_id, "name": name, "value": value})
    return parsed


def serialize_custom_contact_methods(methods: list[dict[str, str]]) -> str:
    return json.dumps(methods, ensure_ascii=False)


def make_custom_contact_methods(payload: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    prepared: list[dict[str, str]] = []
    if not payload:
        return prepared
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            continue
        name = _normalize_text(str(row.get("name") or ""))
        value = _normalize_text(str(row.get("value") or ""))
        if not name or not value:
            continue
        method_id = _normalize_text(str(row.get("id") or "")) or f"custom-{index + 1}"
        prepared.append({"id": method_id, "name": name[:40], "value": value[:255]})
    return prepared


def available_contact_methods(profile: UserProfile) -> list[dict[str, str]]:
    methods: list[dict[str, str]] = []
    if profile.telegram_username:
        methods.append(
            {
                "id": "telegram",
                "name": "Telegram",
                "value": f"@{profile.telegram_username.replace('@', '').strip()}",
            }
        )
    methods.extend(parse_custom_contact_methods(profile.contact_methods_json))
    return methods


def exposed_contact_methods(profile: UserProfile) -> list[dict[str, str]]:
    methods = available_contact_methods(profile)
    if not methods:
        return []

    visibility = (profile.contact_visibility or CONTACT_VISIBILITY_ALL).strip().lower()
    if visibility == CONTACT_VISIBILITY_ONE:
        selected_id = _normalize_text(profile.contact_visibility_method_id)
        if selected_id:
            selected = next((row for row in methods if row["id"] == selected_id), None)
            if selected:
                return [selected]
    return methods


def primary_contact_text(profile: UserProfile) -> str | None:
    exposed = exposed_contact_methods(profile)
    if not exposed:
        return None
    preferred = exposed[0]
    return f"{preferred['name']}: {preferred['value']}"[:80]


def exposed_contact_summary(profile: UserProfile) -> str | None:
    exposed = exposed_contact_methods(profile)
    if not exposed:
        return None
    return " | ".join(f"{row['name']}: {row['value']}" for row in exposed)[:255]
