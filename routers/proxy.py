# Add to your router (e.g., in a new file: api/routes/proxy.py)
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()

ALLOWED_HOST = "res.cloudinary.com"


@router.get("/proxy/image")
async def proxy_image(url: str):
    if ALLOWED_HOST not in url:
        raise HTTPException(status_code=400, detail="Invalid image host")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0, follow_redirects=True)
            response.raise_for_status()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Image fetch timeout")

    return StreamingResponse(
        iter([response.content]),
        media_type=response.headers.get("content-type", "image/jpeg"),
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "CDN-Cache-Control": "public, max-age=31536000",
        },
    )
