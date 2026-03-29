import httpx


class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    async def create_item(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{self.base_url}/items", json=payload)
            response.raise_for_status()
            return response.json()

    async def list_items(self, params: dict | None = None) -> list[dict]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{self.base_url}/items", params=params or {})
            response.raise_for_status()
            return response.json()

    async def search_items(self, query: str) -> list[dict]:
        return await self.list_items({"q": query})

    async def get_matches(self, item_id: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{self.base_url}/items/matches/{item_id}")
            response.raise_for_status()
            return response.json()
