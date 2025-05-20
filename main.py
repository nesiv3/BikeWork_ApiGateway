import asyncio
from fastapi import FastAPI, APIRouter
from core.config import settings
from api.routes import create_proxy_route
from utils.openapi_loader import fetch_openapi_spec

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

@app.on_event("startup")
async def startup_event():
    await load_routes_from_openapi()
    asyncio.create_task(periodic_reload())

async def periodic_reload():
    while True:
        await asyncio.sleep(8 * 60 * 60)
        print("[INFO] Recargando rutas desde OpenAPI...")
        await load_routes_from_openapi()