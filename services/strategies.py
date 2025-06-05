from fastapi import Request
from starlette.responses import Response
from services.proxy_strategy import ProxyStrategy
from services.proxy import proxy_request

class DefaultProxyStrategy(ProxyStrategy):
    async def proxy(self, request: Request, target_url: str) -> Response:
        return await proxy_request(request, target_url)

# Puedes agregar más estrategias, por ejemplo:
class LoggingProxyStrategy(ProxyStrategy):
    async def proxy(self, request: Request, target_url: str) -> Response:
        print(f"[LOG] Proxying to {target_url}")
        return await proxy_request(request, target_url)