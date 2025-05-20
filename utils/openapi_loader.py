import httpx

async def fetch_openapi_spec(openapi_url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(openapi_url, timeout=10.0)
        response.raise_for_status()
        return response.json()