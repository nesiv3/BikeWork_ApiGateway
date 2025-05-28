from fastapi import APIRouter, Request, Path
from fastapi.routing import APIRoute
import inspect
from services.proxy import proxy_request
from services.strategies import DefaultProxyStrategy, LoggingProxyStrategy

def select_strategy(path: str, method: str):
    # Ejemplo: usa LoggingProxyStrategy para endpoints críticos
    if "/schedule" in path:
        return LoggingProxyStrategy()
    if "/store" in path:
        return LoggingProxyStrategy()
    if "/user" in path:
        return LoggingProxyStrategy()
    if "/param" in path:
        return LoggingProxyStrategy()
    return DefaultProxyStrategy()

def make_endpoint(path: str, base_url: str, path_params: list, prefix: str = ""):
    async def endpoint(request: Request, **kwargs):
        final_path = path
        for param in path_params:
            final_path = final_path.replace(f"{{{param}}}", str(kwargs[param]))
        if prefix and final_path.startswith(prefix):
            backend_path = final_path[len(prefix):]
        else:
            backend_path = final_path
        full_url = f"{base_url}{backend_path}"
        strategy = select_strategy(path, request.method)
        return await strategy.proxy(request, full_url)
    return endpoint

def create_proxy_route(path: str, method: str, base_url: str, summary: str = "", prefix: str = "") -> APIRoute:
    path_params = [part[1:-1] for part in path.split("/") if part.startswith("{") and part.endswith("}")]
    endpoint = make_endpoint(path, base_url, path_params, prefix)
    params = [
        inspect.Parameter(
            name=param,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=Path(...),
            annotation=str
        )
        for param in path_params
    ]
    params.insert(0, inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request))
    endpoint.__signature__ = inspect.Signature(parameters=params)
    fastapi_path = path
    return APIRoute(
        path=fastapi_path,
        endpoint=endpoint,
        methods=[method.upper()],
        summary=f"[Proxy] {summary or method.upper()} {path}"
    )