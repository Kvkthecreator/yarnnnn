"""
yarnnn-output-gateway — Output gateway for agent artifact production.

POST /render  — ADR-118: Skills convert structured input to binary files.
POST /compose — ADR-130: HTML composition engine (markdown + assets → styled HTML).
GET /skills/{name}/SKILL.md — skill instructions for agent context injection.

Hardening (ADR-118 D.2):
- Service-to-service auth via shared secret (X-Render-Secret header)
- Request size limits (5MB max payload)
- User-scoped storage paths ({user_id}/{date}/{filename}.{ext})
- In-memory rate limiting (60 requests/minute per caller)
"""

import logging
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional

import importlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="yarnnn-output-gateway", version="3.0.0")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
STORAGE_BUCKET = "agent-outputs"

# ADR-118 D.2: Service-to-service auth
RENDER_SECRET = os.environ.get("RENDER_SERVICE_SECRET", "")

# ADR-118 D.2: Rate limiting (in-memory sliding window)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 60  # requests per window
_rate_limit_store: dict[str, list[float]] = defaultdict(list)

# ADR-118 D.2: Max request payload size (5MB)
MAX_REQUEST_SIZE = 5 * 1024 * 1024

# Skill folder root for serving SKILL.md files
SKILLS_DIR = Path(__file__).parent / "skills"


def _discover_skills() -> dict:
    """ADR-118 D.4: Auto-discover skills from skills/ directory.

    Scans for folders with SKILL.md + scripts/render.py.
    Each skill folder must have a render function named render_{folder_name}.
    Returns {skill_type: render_function} dict.

    Also reads SKILL.md frontmatter for the skill's 'name' field to map
    skill types (e.g., "document") to folder names (e.g., "pdf").
    """
    skills = {}
    type_to_folder = {}

    for folder in sorted(SKILLS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        skill_md = folder / "SKILL.md"
        render_py = folder / "scripts" / "render.py"
        if not skill_md.exists() or not render_py.exists():
            continue

        folder_name = folder.name

        # Read SKILL.md frontmatter for skill type name
        skill_type = folder_name  # default: folder name IS the type
        try:
            content = skill_md.read_text(encoding="utf-8")
            if content.startswith("---"):
                end = content.index("---", 3)
                frontmatter_text = content[3:end]
                for line in frontmatter_text.strip().split("\n"):
                    if line.startswith("name:"):
                        val = line.split(":", 1)[1].strip().strip('"').strip("'")
                        if val:
                            skill_type = val
                        break
        except Exception:
            pass

        # Dynamic import
        try:
            module = importlib.import_module(f"skills.{folder_name}.scripts.render")
            render_fn = getattr(module, f"render_{folder_name}", None)
            if render_fn is None:
                logger.warning(f"[SKILLS] No render_{folder_name}() in {render_py}")
                continue
            skills[skill_type] = render_fn
            type_to_folder[skill_type] = folder_name
            logger.info(f"[SKILLS] Discovered: {skill_type} → skills/{folder_name}/")
        except Exception as e:
            logger.error(f"[SKILLS] Failed to load skills/{folder_name}/: {e}")

    return skills, type_to_folder


# ADR-118 D.4: Auto-discovered skill registry (replaces hard-coded SKILLS dict)
SKILLS, SKILL_TYPE_TO_FOLDER = _discover_skills()


def _check_rate_limit(caller_id: str) -> bool:
    """ADR-118 D.2: Sliding window rate limiter. Returns True if allowed."""
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW
    timestamps = _rate_limit_store[caller_id]
    # Prune expired entries
    _rate_limit_store[caller_id] = [t for t in timestamps if t > window_start]
    if len(_rate_limit_store[caller_id]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_store[caller_id].append(now)
    return True


def _validate_render_secret(request: Request) -> None:
    """ADR-118 D.2: Validate service-to-service auth on POST /render."""
    if not RENDER_SECRET:
        return  # Secret not configured — allow (dev mode)
    provided = request.headers.get("X-Render-Secret", "")
    if provided != RENDER_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Render-Secret")


class RenderRequest(BaseModel):
    type: str  # document, presentation, spreadsheet, chart
    input: dict  # skill-specific spec
    output_format: str  # pdf, docx, pptx, xlsx, png, svg
    template_id: Optional[str] = None
    filename: Optional[str] = None  # optional custom filename
    user_id: Optional[str] = None  # ADR-118 D.2: user scoping for storage paths


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
        # Use PUT for upsert — overwrites if file exists (ADR-157: re-fetch support)
        resp = await client.put(upload_url, content=file_bytes, headers=headers)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Storage upload HTTP {resp.status_code}: {resp.text}")

    return f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{storage_path}"


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "skills": list(SKILLS.keys()),
        "compose": True,
        "surface_types": ["report", "deck", "dashboard", "digest", "workbook", "preview", "video"],
        "storage": bool(SUPABASE_URL and SUPABASE_SERVICE_KEY),
    }


@app.get("/skills/{name}/SKILL.md", response_class=PlainTextResponse)
async def get_skill_md(name: str):
    """Serve SKILL.md content for agent context injection (ADR-118 D.1).

    The execution pipeline fetches this to inject skill instructions into
    the agent's context, so agents learn how to construct high-quality specs.
    """
    skill_path = SKILLS_DIR / name / "SKILL.md"
    if not skill_path.exists():
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    return skill_path.read_text(encoding="utf-8")


@app.get("/skills")
async def list_skills():
    """List available skills with type→folder mapping.

    ADR-118 D.4: Returns both folder names and the type mapping
    so the API can dynamically build RuntimeDispatch schema.
    """
    return {
        "skills": sorted(SKILLS.keys()),
        "type_to_folder": SKILL_TYPE_TO_FOLDER,
    }


@app.post("/render", response_model=RenderResponse)
async def render(req: RenderRequest, request: Request):
    # ADR-118 D.2: Service-to-service auth
    _validate_render_secret(request)

    # ADR-118 D.2: Rate limiting
    caller_id = req.user_id or request.client.host if request.client else "unknown"
    if not _check_rate_limit(caller_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded (60 req/min)")

    # ADR-118 D.2: Request size limit (check content-length header)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        raise HTTPException(status_code=413, detail=f"Request too large (max {MAX_REQUEST_SIZE // 1024 // 1024}MB)")

    skill_fn = SKILLS.get(req.type)
    if not skill_fn:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown skill type: {req.type}. Available: {list(SKILLS.keys())}",
        )

    try:
        file_bytes, content_type = await skill_fn(req.input, req.output_format)
    except ValueError as e:
        return RenderResponse(success=False, error=str(e))
    except Exception as e:
        logger.error(f"[RENDER] Skill {req.type} failed: {e}")
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
        # ADR-118 D.2: User-scoped storage paths
        user_prefix = req.user_id or "anonymous"
        storage_path = f"{user_prefix}/{date_prefix}/{filename}.{ext}"

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


# ---------------------------------------------------------------------------
# ADR-130: HTML Composition Engine
# ADR-213: Content-addressed cache for surface-pull composition
# ---------------------------------------------------------------------------

import hashlib

from compose import ComposeRequest, ComposeResponse, compose_html, COMPOSE_ENGINE_VERSION


def _compose_cache_key(req: ComposeRequest) -> str:
    """ADR-213: content-addressed cache key for /compose.

    Hashes all inputs that affect output. Any substrate change (new sections,
    new assets, brand CSS edit) or engine bump produces a new hash, so the
    cache invalidates automatically with no explicit eviction code.
    """
    payload = {
        "v": COMPOSE_ENGINE_VERSION,
        "surface_type": req.surface_type,
        "title": req.title,
        "brand_css": req.brand_css or "",
        "markdown": req.markdown or "",
        "sections": [
            {"kind": s.kind, "title": s.title, "content": s.content}
            for s in (req.sections or [])
        ],
        "assets": sorted(
            [{"ref": a.get("ref", ""), "url": a.get("url", "")} for a in (req.assets or [])],
            key=lambda a: a["ref"],
        ),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


async def _compose_cache_get(hash_key: str) -> Optional[bytes]:
    """Read cached composed HTML from Supabase Storage. None on miss or error."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        return None
    url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/_compose-cache/{hash_key}.html"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.content
    except Exception as e:
        logger.warning(f"[COMPOSE] Cache read error for {hash_key[:12]}: {e}")
    return None


async def _compose_cache_put(hash_key: str, html_bytes: bytes) -> Optional[str]:
    """Write composed HTML to content-addressed cache. Returns public URL or None."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        return None
    try:
        storage_path = f"_compose-cache/{hash_key}.html"
        return await _upload_to_storage(html_bytes, storage_path, "text/html")
    except Exception as e:
        logger.warning(f"[COMPOSE] Cache write error for {hash_key[:12]}: {e}")
        return None


# import json at module scope for cache key serialization
import json


@app.post("/compose", response_model=ComposeResponse)
async def compose(req: ComposeRequest, request: Request):
    """ADR-130 + ADR-213: Compose markdown/sections + assets into styled HTML.

    Surface types: report (default), deck, dashboard, digest, workbook, preview, video.

    Content-addressed cache short-circuits repeat composes of identical
    substrate — hash on sections + surface_type + assets + brand_css +
    engine version. Cache storage: Supabase `{bucket}/_compose-cache/{hash}.html`.
    No explicit invalidation — substrate changes produce new hashes.
    """
    _validate_render_secret(request)

    caller_id = req.user_id or (request.client.host if request.client else "unknown")
    if not _check_rate_limit(caller_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded (60 req/min)")

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        raise HTTPException(status_code=413, detail=f"Request too large (max {MAX_REQUEST_SIZE // 1024 // 1024}MB)")

    valid_surfaces = ("report", "deck", "dashboard", "digest", "workbook", "preview", "video")
    if req.surface_type not in valid_surfaces:
        return ComposeResponse(
            success=False,
            error=f"Invalid surface_type: {req.surface_type}. Valid: {valid_surfaces}",
        )

    # ADR-213: content-addressed cache hit
    cache_key = _compose_cache_key(req)
    cached = await _compose_cache_get(cache_key)
    if cached is not None:
        logger.info(f"[COMPOSE] Cache hit {cache_key[:12]} ({len(cached)} bytes)")
        cache_url = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/_compose-cache/{cache_key}.html"
        return ComposeResponse(
            success=True,
            html=cached.decode("utf-8"),
            output_url=cache_url,
            content_type="text/html",
            size_bytes=len(cached),
        )

    try:
        html = compose_html(
            md_text=req.markdown,
            title=req.title,
            surface_type=req.surface_type,
            assets=req.assets or [],
            brand_css=req.brand_css,
            # ADR-177 Phase D1: pass sections when provided; render service
            # dispatches on kind. Falls back to flat markdown when sections absent.
            sections=req.sections if req.sections else None,
        )
    except Exception as e:
        logger.error(f"[COMPOSE] Composition failed: {e}")
        return ComposeResponse(success=False, error=f"Composition failed: {str(e)}")

    html_bytes = html.encode("utf-8")
    size_bytes = len(html_bytes)

    # ADR-213: populate cache (best-effort — miss does not block response)
    cache_url = await _compose_cache_put(cache_key, html_bytes)
    if cache_url:
        logger.info(f"[COMPOSE] Cache miss → stored {cache_key[:12]} ({size_bytes} bytes)")

    return ComposeResponse(
        success=True,
        html=html,
        output_url=cache_url,
        content_type="text/html",
        size_bytes=size_bytes,
    )
