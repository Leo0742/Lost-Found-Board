from urllib.parse import quote


def yandex_maps_route_url(latitude: float | None = None, longitude: float | None = None, address_text: str | None = None) -> str | None:
    if latitude is not None and longitude is not None:
        return f"https://yandex.com/maps/?rtext=~{latitude},{longitude}&rtt=auto"
    text = (address_text or "").strip()
    if not text:
        return None
    return f"https://yandex.com/maps/?text={quote(text)}&rtt=auto"
