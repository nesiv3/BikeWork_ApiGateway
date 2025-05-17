from fastapi import APIRouter, FastAPI, Request, Path
from fastapi.routing import APIRoute
import httpx
from fastapi.responses import JSONResponse
from starlette.responses import Response
from typing import List
import inspect

import os
from dotenv import load_dotenv

load_dotenv()

OPENAPI_URLS = [
    url.strip() for url in os.getenv("OPENAPI_URLS", "").split("||") if url.strip()
]

app = FastAPI(title="Dynamic API Gateway", version="1.0.4")
routes_loaded: List[dict] = []
api_router = APIRouter()

@api_router.get("/api_uris")
async def list_loaded_uris():
    return {"loaded_routes": routes_loaded}

@app.get("/")
async def root():
    return {
        "message": "Dynamic API Gateway is running",
        "routes_loaded": len(routes_loaded)
    }

async def proxy(request: Request, target_url: str) -> Response:
    async with httpx.AsyncClient() as client:
        method = request.method
        headers = dict(request.headers)
        # Elimina headers problemáticos
        headers.pop("host", None)
        headers.pop("content-length", None)
        body = await request.body()
        try:
            resp = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params,
                timeout=10.0
            )
            # Devuelve JSON si es posible, si no, devuelve el contenido tal cual
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                return JSONResponse(
                    status_code=resp.status_code,
                    content=resp.json(),
                    headers=resp.headers
                )
            else:
                return Response(
                    content=resp.content,
                    status_code=resp.status_code,
                    headers=resp.headers
                )
        except httpx.RequestError as exc:
            return JSONResponse(
                status_code=502,
                content={"detail": f"Error forwarding request to {target_url}: {str(exc)}"}
            )

def make_endpoint(path: str, base_url: str, path_params: List[str]):
    async def endpoint(request: Request, **kwargs):
        final_path = path
        for param in path_params:
            final_path = final_path.replace(f"{{{param}}}", str(kwargs[param]))
        full_url = f"{base_url}{final_path}"
        return await proxy(request, full_url)
    return endpoint

def create_proxy_route(path: str, method: str, base_url: str, summary: str = "") -> APIRoute:
    path_params = [part[1:-1] for part in path.split("/") if part.startswith("{") and part.endswith("}")]

    endpoint = make_endpoint(path, base_url, path_params)

    # Construir signature con los path params explícitos para FastAPI
    params = [
        inspect.Parameter(
            name=param,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=Path(...),
            annotation=str
        )
        for param in path_params
    ]

    # Añadimos el parámetro request (FastAPI lo inyecta)
    params.insert(0, inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request))

    endpoint.__signature__ = inspect.Signature(parameters=params)

    fastapi_path = path  # ya con {param} como debe ser

    return APIRoute(
        path=fastapi_path,
        endpoint=endpoint,
        methods=[method.upper()],
        summary=f"[Proxy] {summary or method.upper()} {path}"
    )

async def load_routes_from_openapi():
    global routes_loaded
    routes_loaded.clear()

    for openapi_url in OPENAPI_URLS:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(openapi_url, timeout=10.0)
                response.raise_for_status()
                spec = response.json()

                # Detecta el nombre del microservicio (puedes ajustar esto según tu naming)
                if "store" in openapi_url:
                    prefix = "/store"
                elif "user" in openapi_url:
                    prefix = "/user"
                elif "param" in openapi_url:
                    prefix = "/param"
                elif "schedule" in openapi_url:
                    prefix = "/schedule"
                else:
                    prefix = ""

                servers = spec.get("servers", [])
                if servers and "url" in servers[0]:
                    base_url = servers[0]["url"].rstrip("/")
                else:
                    base_url = openapi_url.replace("/openapi.json", "")

                for path, path_item in spec.get("paths", {}).items():
                    for method, operation in path_item.items():
                        # Agrega el prefijo antes de /api
                        if path.startswith("/api"):
                            fastapi_path = f"{prefix}{path}"
                        else:
                            fastapi_path = f"{prefix}/api{path}"
                        route = create_proxy_route(
                            fastapi_path, method, base_url, operation.get("summary", "")
                        )
                        app.router.routes.append(route)
                        routes_loaded.append({
                            "method": method.upper(),
                            "path": fastapi_path,
                            "url": f"{base_url}{path}"
                        })

                print(f"[INFO] Loaded routes from {openapi_url} - total {len(spec.get('paths',{}))} paths")

        except Exception as e:
            print(f"[WARN] Cannot load OpenAPI spec from {openapi_url}: {e}")


app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    await load_routes_from_openapi()
