import uuid
from datetime import datetime
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
import httpx
from core.logging import log_request

async def proxy_request(request: Request, target_url: str) -> Response:
    log_id = str(uuid.uuid4())
    request_body = (await request.body()).decode("utf-8", errors="ignore")
    log_data = {
        "log_id": log_id,
        "method": request.method,
        "path": request.url.path,
        "query": dict(request.query_params),
        "target_url": target_url,
        "client": request.client.host if request.client else None,
        "request_headers": dict(request.headers),
        "request_body": request_body,
        "timestamp_request": datetime.now(),
    }
    async with httpx.AsyncClient() as client:
        method = request.method
        headers = dict(request.headers)
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
            content_type = resp.headers.get("content-type", "")
            try:
                response_body = resp.json()
            except Exception:
                response_body = resp.text
            log_data.update({
                "response_status": resp.status_code,
                "response_headers": dict(resp.headers),
                "response_body": response_body,
                "error": None,
                "timestamp_response": datetime.now()
            })
            log_request(log_data)
            if "application/json" in content_type:
                return JSONResponse(
                    status_code=resp.status_code,
                    content=response_body,
                    headers=resp.headers
                )
            else:
                return Response(
                    content=resp.content,
                    status_code=resp.status_code,
                    headers=resp.headers
                )
        except httpx.RequestError as exc:
            log_data.update({
                "response_status": 502,
                "response_headers": {},
                "response_body": None,
                "error": str(exc),
                "timestamp_response": datetime.now()
            })
            log_request(log_data)
            return JSONResponse(
                status_code=502,
                content={"detail": f"Error forwarding request to {target_url}: {str(exc)}"}
            )