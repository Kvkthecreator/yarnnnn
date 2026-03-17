"""
yarnnn-render — Lightweight render service for agent artifact production (ADR-118).

Single POST /render endpoint. Handlers convert structured input to binary files.
Uploads results to Supabase Storage and returns the URL.
"""

import logging
import os
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from handlers import HANDLERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="yarnnn-render", version="1.0.0")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
STORAGE_BUCKET = "agent-outputs"


class RenderRequest(BaseModel):
    type: str  # document, presentation, spreadsheet, chart
    input: dict  # handler-specific spec
    output_format: str  # pdf, docx, pptx, xlsx, png, svg
    template_id: Optional[str] = None
    filename: Optional[str] = None  # optional custom filename


class RenderResponse(BaseModel):
    success: bool
    output_url: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    error: Optional[str] = None


async def _upload_to_storage(file_bytes: bytes, storage_path: str, content_type: str) -> str:
    """Upload file to Supabase Storage via REST API and return public URL.

    Uses direct HTTP instead of supabase-py client because the service key
    may be in sb_secret_ format (not a JWT), which the Python client's storage
    module rejects. The REST API accepts it via apikey + Authorization headers.
    """
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{storage_path}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(upload_url, content=file_bytes, headers=headers)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Storage upload HTTP {resp.status_code}: {resp.text}")

    return f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{storage_path}"


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "handlers": list(HANDLERS.keys()),
        "storage": bool(SUPABASE_URL and SUPABASE_SERVICE_KEY),
    }


@app.post("/render", response_model=RenderResponse)
async def render(req: RenderRequest):
    handler = HANDLERS.get(req.type)
    if not handler:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown handler type: {req.type}. Available: {list(HANDLERS.keys())}",
        )

    try:
        file_bytes, content_type = await handler(req.input, req.output_format)
    except ValueError as e:
        return RenderResponse(success=False, error=str(e))
    except Exception as e:
        logger.error(f"[RENDER] Handler {req.type} failed: {e}")
        return RenderResponse(success=False, error=f"Render failed: {str(e)}")

    # Upload to Supabase Storage
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return RenderResponse(
            success=False,
            error="Storage not configured (missing SUPABASE_URL or SUPABASE_SERVICE_KEY)",
        )

    try:
        date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        ext = req.output_format
        filename = req.filename or f"{req.type}-{uuid.uuid4().hex[:8]}"
        storage_path = f"{date_prefix}/{filename}.{ext}"

        output_url = await _upload_to_storage(file_bytes, storage_path, content_type)

        return RenderResponse(
            success=True,
            output_url=output_url,
            content_type=content_type,
            size_bytes=len(file_bytes),
        )
    except Exception as e:
        logger.error(f"[RENDER] Storage upload failed: {e}")
        return RenderResponse(success=False, error=f"Storage upload failed: {str(e)}")
