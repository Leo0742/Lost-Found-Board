import httpx


class BackendClient:
    def __init__(self, base_url: str, timeout_seconds: float = 15.0, match_timeout_seconds: float = 45.0):
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.match_timeout_seconds = match_timeout_seconds

    async def create_item(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/items", json=payload)
            response.raise_for_status()
            return response.json()

    async def upload_item_image(self, content: bytes, filename: str = "telegram.jpg", mime_type: str = "image/jpeg") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            files = {"image": (filename, content, mime_type)}
            response = await client.post(f"{self.base_url}/items/upload-image", files=files)
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
            response = await client.get(f"{self.base_url}/items/matches/{item_id}")
            response.raise_for_status()
            return response.json()

    async def list_my_items(self, telegram_user_id: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/items/mine/{telegram_user_id}")
            response.raise_for_status()
            return response.json()

    async def resolve_item(self, item_id: int, telegram_user_id: int) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/items/{item_id}/resolve",
                json={"telegram_user_id": telegram_user_id},
            )
            response.raise_for_status()
            return response.json()

    async def reopen_item(self, item_id: int, telegram_user_id: int) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/items/{item_id}/reopen",
                json={"telegram_user_id": telegram_user_id},
            )
            response.raise_for_status()
            return response.json()

    async def delete_item(self, item_id: int, telegram_user_id: int) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/items/{item_id}/delete",
                json={"telegram_user_id": telegram_user_id},
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
                f"{self.base_url}/items/claim-requests",
                json={
                    "source_item_id": source_item_id,
                    "target_item_id": target_item_id,
                    "requester_telegram_user_id": requester_telegram_user_id,
                    "claim_message": claim_message or None,
                },
            )
            response.raise_for_status()
            return response.json()

    async def list_claims(self, telegram_user_id: int, direction: str = "all") -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}/items/claim-requests",
                params={"telegram_user_id": telegram_user_id, "direction": direction},
            )
            response.raise_for_status()
            return response.json()

    async def claim_action(self, claim_id: int, action: str, telegram_user_id: int, note: str = "") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/items/claim-requests/{claim_id}/{action}",
                json={"telegram_user_id": telegram_user_id, "note": note or None},
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
