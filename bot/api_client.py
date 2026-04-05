import httpx


class BackendClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 15.0,
        match_timeout_seconds: float = 45.0,
        internal_api_token: str | None = None,
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.match_timeout_seconds = match_timeout_seconds
        self.internal_api_token = internal_api_token

    @property
    def _internal_headers(self) -> dict[str, str]:
        if not self.internal_api_token:
            return {}
        return {"X-Internal-Token": self.internal_api_token}

    async def create_item(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/items", json=payload)
            response.raise_for_status()
            return response.json()

    async def upload_item_image(self, content: bytes, filename: str = "telegram.jpg", mime_type: str = "image/jpeg") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            files = {"image": (filename, content, mime_type)}
            response = await client.post(f"{self.base_url}/items/upload-image", files=files, headers=self._internal_headers)
            response.raise_for_status()
            return response.json()

    async def fetch_media_bytes(self, image_path: str) -> tuple[bytes, str]:
        media_base_url = self.base_url.removesuffix("/api")
        normalized_path = image_path.lstrip("/")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{media_base_url}/media/{normalized_path}")
            response.raise_for_status()
            return response.content, response.headers.get("content-type", "application/octet-stream")

    async def list_items(self, params: dict | None = None) -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/items", params=params or {})
            response.raise_for_status()
            return response.json()

    async def search_items(self, query: str) -> list[dict]:
        return await self.list_items({"q": query})

    async def search_items_smart(self, query: str, limit: int = 8) -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/items/search-smart", params={"q": query, "limit": limit})
            response.raise_for_status()
            return response.json()

    async def get_categories(self) -> list[str]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/items/categories")
            response.raise_for_status()
            return response.json()

    async def suggest_category(self, title: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/items/category-suggest", params={"title": title})
            response.raise_for_status()
            return response.json()

    async def get_matches(self, item_id: int) -> list[dict] | None:
        async with httpx.AsyncClient(timeout=self.match_timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/items/internal/matches/{item_id}", headers=self._internal_headers)
            response.raise_for_status()
            return response.json()

    async def list_my_items(self, telegram_user_id: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/items/internal/mine/{telegram_user_id}", headers=self._internal_headers)
            response.raise_for_status()
            return response.json()

    async def get_profile_internal(self, telegram_user_id: int) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}/profile/internal/{telegram_user_id}",
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()

    async def sync_telegram_profile(
        self,
        telegram_user_id: int,
        telegram_username: str | None,
        telegram_display_name: str | None,
        telegram_avatar_url: str | None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/profile/internal/sync-telegram",
                json={
                    "telegram_user_id": telegram_user_id,
                    "telegram_username": telegram_username,
                    "telegram_display_name": telegram_display_name,
                    "telegram_avatar_url": telegram_avatar_url,
                },
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()

    async def resolve_item(self, item_id: int, telegram_user_id: int) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/items/internal/{item_id}/resolve",
                json={"telegram_user_id": telegram_user_id},
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()

    async def reopen_item(self, item_id: int, telegram_user_id: int) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/items/internal/{item_id}/reopen",
                json={"telegram_user_id": telegram_user_id},
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()

    async def delete_item(self, item_id: int, telegram_user_id: int) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/items/internal/{item_id}/delete",
                json={"telegram_user_id": telegram_user_id},
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()

    async def flag_item(self, item_id: int, reason: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/items/{item_id}/flag", json={"reason": reason})
            response.raise_for_status()
            return response.json()

    async def create_claim(self, source_item_id: int, target_item_id: int, requester_telegram_user_id: int, claim_message: str = "") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/items/internal/claim-requests",
                json={
                    "source_item_id": source_item_id,
                    "target_item_id": target_item_id,
                    "requester_telegram_user_id": requester_telegram_user_id,
                    "claim_message": claim_message or None,
                },
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_claims(self, telegram_user_id: int, direction: str = "all") -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}/items/internal/claim-requests",
                params={"telegram_user_id": telegram_user_id, "direction": direction},
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()

    async def claim_action(self, claim_id: int, action: str, telegram_user_id: int, note: str = "") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/items/internal/claim-requests/{claim_id}/{action}",
                json={"telegram_user_id": telegram_user_id, "note": note or None},
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()


    async def share_claim_live_location(self, claim_id: int, telegram_user_id: int, latitude: float, longitude: float, address_text: str | None = None, ttl_minutes: int = 120) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/items/internal/claim-requests/{claim_id}/share-live-location",
                json={
                    "telegram_user_id": telegram_user_id,
                    "latitude": latitude,
                    "longitude": longitude,
                    "address_text": address_text,
                    "ttl_minutes": ttl_minutes,
                },
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()
    async def confirm_web_link(self, code: str, telegram_user_id: int, telegram_username: str | None, display_name: str | None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/auth/link/confirm",
                json={
                    "code": code,
                    "telegram_user_id": telegram_user_id,
                    "telegram_username": telegram_username,
                    "display_name": display_name,
                },
            )
            response.raise_for_status()
            return response.json()

    async def telegram_admin_access(self, telegram_user_id: int, telegram_username: str | None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}/auth/telegram-admin-access",
                params={"telegram_user_id": telegram_user_id, "telegram_username": telegram_username},
            )
            response.raise_for_status()
            return response.json()
