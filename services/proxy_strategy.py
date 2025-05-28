from fastapi import Request
from starlette.responses import Response

class ProxyStrategy:
    async def proxy(self, request: Request, target_url: str) -> Response:
        raise NotImplementedError