import asyncio
import uuid
from fastapi import FastAPI, APIRouter
from core.config import settings
from api.routes import create_proxy_route
from utils.openapi_loader import fetch_openapi_spec
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi.exception_handlers import RequestValidationError
from fastapi import status

app = FastAPI(title="Dynamic API Gateway", version="1.0.4")
routes_loaded = []
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

async def load_routes_from_openapi():
    global routes_loaded
    routes_loaded.clear()
    for openapi_url in settings.OPENAPI_URLS:
        try:
            spec = await fetch_openapi_spec(openapi_url)
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
                    if path.startswith("/api"):
                        fastapi_path = f"{prefix}{path}"
                    else:
                        fastapi_path = f"{prefix}/api{path}"
                    route = create_proxy_route(
                        fastapi_path, method, base_url, operation.get("summary", ""), prefix
                    )
                    app.router.routes.append(route)
                    routes_loaded.append({
                        "method": method.upper(),
                        "path": fastapi_path,
                        "url": f"{base_url}{path}"
                    })
        except Exception as e:
            print(f"[WARN] Cannot load OpenAPI spec from {openapi_url}: {e}")

app.include_router(api_router)

@app.post("/reload_apis")
async def reload_apis():
    await load_routes_from_openapi()
    return {"message": "APIs reloaded successfully", "routes_loaded": len(routes_loaded)}

@app.on_event("shutdown")
async def shutdown_event():
    from services.proxy import get_http_client
    client = get_http_client()
    await client.aclose()

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.on_event("startup")
async def startup_event():
    await load_routes_from_openapi()