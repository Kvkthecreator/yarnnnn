"""
Domain routes - ADR-034 Emergent Context Domains

Endpoints for domain management and memory access.
Domains emerge from deliverable source patterns - users don't manage them directly,
but can view and rename them.

Context v2: Domains replace project-based context scoping.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from services.supabase import UserClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/domains", tags=["domains"])


# =============================================================================
# Response Models
# =============================================================================

class DomainSummary(BaseModel):
    """Summary of a context domain."""
    id: str
    name: str
    name_source: str  # 'auto' or 'user'
    is_default: bool
    source_count: int
    deliverable_count: int
    memory_count: int
    created_at: str


class DomainDetail(BaseModel):
    """Detailed domain info with sources."""
    id: str
    name: str
    name_source: str
    is_default: bool
    sources: list[dict]  # [{provider, resource_id, resource_name}]
    deliverable_ids: list[str]
    memory_count: int
    created_at: str
    updated_at: str


class DomainUpdateRequest(BaseModel):
    """Request to update domain (rename)."""
    name: str


class MemoryResponse(BaseModel):
    """Memory item response."""
    id: str
    content: str
    tags: list[str]
    entities: dict
    importance: float
    source_type: str
    source_ref: Optional[dict] = None
    domain_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MemoryCreate(BaseModel):
    """Request to create a memory."""
    content: str
    tags: list[str] = []
    importance: float = 0.5


class MemoryUpdate(BaseModel):
    """Request to update a memory."""
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    importance: Optional[float] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("")
async def list_domains(auth: UserClient):
    """
    ADR-059: Domains removed as a DB concept.
    Returns empty list — domain grouping is a UI concept on deliverables.
    """
    return {"domains": [], "total": 0}


@router.get("/active")
async def get_active_domain(
    auth: UserClient,
    deliverable_id: Optional[str] = None
):
    """
    ADR-059: Domains removed as a DB concept.
    Returns null domain — callers should treat this as no domain context.
    """
    return {"domain": None, "source": "none", "domain_count": 0}


@router.get("/{domain_id}")
async def get_domain(domain_id: UUID, auth: UserClient):
    # ADR-059: knowledge_domains table removed
    raise HTTPException(status_code=404, detail="Domains not supported (ADR-059)")


@router.patch("/{domain_id}")
async def update_domain(domain_id: UUID, request: DomainUpdateRequest, auth: UserClient):
    # ADR-059: knowledge_domains table removed
    raise HTTPException(status_code=404, detail="Domains not supported (ADR-059)")


@router.post("/recompute")
async def trigger_recompute(auth: UserClient):
    """
    Manually trigger domain recomputation.

    Normally domains are recomputed automatically when deliverables change.
    This endpoint is for admin/debug purposes or after bulk operations.
    """
    # ADR-059: Domain inference removed — domains are a UI concept on deliverables
    return {
        "success": True,
        "changes": {}
    }


# =============================================================================
# Domain Memory Routes (Context v2)
# =============================================================================

@router.get("/{domain_id}/memories")
async def list_domain_memories(domain_id: UUID, auth: UserClient):
    # ADR-059: knowledge_domains removed — return empty list
    return []


@router.post("/{domain_id}/memories")
async def create_domain_memory(domain_id: UUID, memory: MemoryCreate, auth: UserClient):
    # ADR-059: knowledge_domains removed — redirect to user context
    raise HTTPException(status_code=404, detail="Domain memories not supported (ADR-059). Use /api/memory/user/memories instead.")
