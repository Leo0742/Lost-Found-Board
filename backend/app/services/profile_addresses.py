import json
from typing import Any

from app.models.user_profile import UserProfile

ADDRESS_VISIBILITY_ALL = "all"
ADDRESS_VISIBILITY_ONE = "one"


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def parse_profile_addresses(raw_json: str | None) -> list[dict[str, Any]]:
    if not raw_json:
        return []
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []

    parsed: list[dict[str, Any]] = []
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            continue
        label = _normalize_text(str(row.get("label") or ""))
        address_text = _normalize_text(str(row.get("address_text") or ""))
        if not address_text:
            continue
        address_id = _normalize_text(str(row.get("id") or "")) or f"addr-{index + 1}"
        latitude = row.get("latitude")
        longitude = row.get("longitude")
        parsed.append(
            {
                "id": address_id[:64],
                "label": (label or "Address")[:40],
                "address_text": address_text[:255],
                "latitude": float(latitude) if isinstance(latitude, (float, int)) else None,
                "longitude": float(longitude) if isinstance(longitude, (float, int)) else None,
                "extra_details": _normalize_text(str(row.get("extra_details") or ""))[:500] if row.get("extra_details") else None,
            }
        )
    return parsed


def serialize_profile_addresses(addresses: list[dict[str, Any]]) -> str:
    return json.dumps(addresses, ensure_ascii=False)


def make_profile_addresses(payload: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    if not payload:
        return prepared
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            continue
        label = _normalize_text(str(row.get("label") or "")) or "Address"
        address_text = _normalize_text(str(row.get("address_text") or ""))
        if not address_text:
            continue
        address_id = _normalize_text(str(row.get("id") or "")) or f"addr-{index + 1}"
        latitude = row.get("latitude")
        longitude = row.get("longitude")
        prepared.append(
            {
                "id": address_id[:64],
                "label": label[:40],
                "address_text": address_text[:255],
                "latitude": float(latitude) if isinstance(latitude, (float, int)) else None,
                "longitude": float(longitude) if isinstance(longitude, (float, int)) else None,
                "extra_details": _normalize_text(str(row.get("extra_details") or ""))[:500] if row.get("extra_details") else None,
            }
        )
    return prepared


def available_profile_addresses(profile: UserProfile) -> list[dict[str, Any]]:
    return parse_profile_addresses(profile.profile_addresses_json)


def exposed_profile_addresses(profile: UserProfile) -> list[dict[str, Any]]:
    addresses = available_profile_addresses(profile)
    if not addresses:
        return []

    visibility = (profile.address_visibility or ADDRESS_VISIBILITY_ALL).strip().lower()
    if visibility == ADDRESS_VISIBILITY_ONE:
        selected_id = _normalize_text(profile.address_visibility_address_id)
        if selected_id:
            selected = next((row for row in addresses if row["id"] == selected_id), None)
            if selected:
                return [selected]
    return addresses


def exposed_address_text(profile: UserProfile) -> str | None:
    exposed = exposed_profile_addresses(profile)
    if not exposed:
        return None
    first = exposed[0]
    return str(first.get("address_text") or "")[:160] or None


def exposed_address_summary(profile: UserProfile) -> str | None:
    exposed = exposed_profile_addresses(profile)
    if not exposed:
        return None
    return " | ".join(f"{row.get('label')}: {row.get('address_text')}" for row in exposed)[:255]


def primary_exposed_profile_address(profile: UserProfile) -> dict[str, Any] | None:
    exposed = exposed_profile_addresses(profile)
    return exposed[0] if exposed else None
