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

    async def list_items(self, params: dict | None = None) -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/items", params=params or {})
            response.raise_for_status()
            return response.json()

    async def search_items(self, query: str) -> list[dict]:
        return await self.list_items({"q": query})

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
