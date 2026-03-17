"""
yarnnn-render — Lightweight render service for agent artifact production (ADR-118).

Single POST /render endpoint. Handlers convert structured input to binary files.
Uploads results to Supabase Storage and returns the URL.
"""

import logging
import os
import uuid
from datetime import datetime, timezone

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


def _get_supabase():
    """Lazy init Supabase client."""
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


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
        client = _get_supabase()
        date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        ext = req.output_format
        filename = req.filename or f"{req.type}-{uuid.uuid4().hex[:8]}"
        storage_path = f"{date_prefix}/{filename}.{ext}"

        client.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type},
        )

        output_url = client.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

        return RenderResponse(
            success=True,
            output_url=output_url,
            content_type=content_type,
            size_bytes=len(file_bytes),
        )
    except Exception as e:
        logger.error(f"[RENDER] Storage upload failed: {e}")
        return RenderResponse(success=False, error=f"Storage upload failed: {str(e)}")
