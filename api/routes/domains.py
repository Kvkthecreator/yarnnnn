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
from services.extraction import create_memory_manual

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
    List user's context domains with summary counts.

    Returns all domains including the default "Personal" domain.
    Domains are auto-managed by the system based on deliverable sources.
    """
    try:
        # Get domains summary using the helper function
        result = auth.client.rpc("get_user_domains_summary", {
            "p_user_id": auth.user_id
        }).execute()

        if not result.data:
            return {"domains": [], "total": 0}

        domains = []
        for row in result.data:
            domains.append(DomainSummary(
                id=row["id"],
                name=row["name"],
                name_source=row["name_source"],
                is_default=row["is_default"],
                source_count=row["source_count"],
                deliverable_count=row["deliverable_count"],
                memory_count=row["memory_count"],
                created_at=row["created_at"] if isinstance(row.get("created_at"), str) else (row["created_at"].isoformat() if row.get("created_at") else "")
            ))

        return {
            "domains": domains,
            "total": len(domains)
        }
    except Exception as e:
        logger.error(f"Failed to list domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_domain(
    auth: UserClient,
    deliverable_id: Optional[str] = None
):
    """
    Get the active domain for current context.

    If deliverable_id is provided, returns that deliverable's domain.
    Otherwise, returns the user's only non-default domain if they have exactly one,
    or null if ambiguous.
    """
    try:
        # Priority 1: Deliverable context
        if deliverable_id:
            result = auth.client.rpc("get_deliverable_domain", {
                "p_deliverable_id": deliverable_id
            }).execute()

            if result.data:
                # Get domain details
                domain_result = auth.client.table("knowledge_domains")\
                    .select("id, name, is_default")\
                    .eq("id", result.data)\
                    .single()\
                    .execute()

                if domain_result.data:
                    return {
                        "domain": {
                            "id": domain_result.data["id"],
                            "name": domain_result.data["name"],
                            "is_default": domain_result.data["is_default"]
                        },
                        "source": "deliverable"
                    }

        # Priority 2: Single domain (auto-select)
        domains_result = auth.client.table("knowledge_domains")\
            .select("id, name, is_default")\
            .eq("user_id", auth.user_id)\
            .eq("is_default", False)\
            .execute()

        if domains_result.data and len(domains_result.data) == 1:
            return {
                "domain": {
                    "id": domains_result.data[0]["id"],
                    "name": domains_result.data[0]["name"],
                    "is_default": False
                },
                "source": "single_domain"
            }

        # Ambiguous or no domains
        return {
            "domain": None,
            "source": "ambiguous",
            "domain_count": len(domains_result.data) if domains_result.data else 0
        }
    except Exception as e:
        logger.error(f"Failed to get active domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{domain_id}")
async def get_domain(domain_id: UUID, auth: UserClient):
    """
    Get detailed information about a domain including sources.
    """
    try:
        # Get domain
        domain_result = auth.client.table("knowledge_domains")\
            .select("*")\
            .eq("id", str(domain_id))\
            .eq("user_id", auth.user_id)\
            .single()\
            .execute()

        if not domain_result.data:
            raise HTTPException(status_code=404, detail="Domain not found")

        domain = domain_result.data

        # Get sources
        sources_result = auth.client.table("domain_sources")\
            .select("provider, resource_id, resource_name")\
            .eq("domain_id", str(domain_id))\
            .execute()

        # Get deliverable IDs
        deliverables_result = auth.client.table("deliverable_domains")\
            .select("deliverable_id")\
            .eq("domain_id", str(domain_id))\
            .execute()

        # Get memory count
        memories_result = auth.client.table("knowledge_entries")\
            .select("id", count="exact")\
            .eq("domain_id", str(domain_id))\
            .eq("is_active", True)\
            .execute()

        return DomainDetail(
            id=domain["id"],
            name=domain["name"],
            name_source=domain["name_source"],
            is_default=domain["is_default"],
            sources=sources_result.data or [],
            deliverable_ids=[d["deliverable_id"] for d in deliverables_result.data or []],
            memory_count=memories_result.count or 0,
            created_at=domain["created_at"],
            updated_at=domain["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get domain {domain_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{domain_id}")
async def update_domain(domain_id: UUID, request: DomainUpdateRequest, auth: UserClient):
    """
    Update a domain (currently only name can be changed).

    When user renames a domain, name_source changes to 'user' to preserve
    the custom name during domain recomputation.
    """
    try:
        # Verify ownership
        check_result = auth.client.table("knowledge_domains")\
            .select("id")\
            .eq("id", str(domain_id))\
            .eq("user_id", auth.user_id)\
            .single()\
            .execute()

        if not check_result.data:
            raise HTTPException(status_code=404, detail="Domain not found")

        # Update name
        result = auth.client.table("knowledge_domains")\
            .update({
                "name": request.name,
                "name_source": "user"  # Mark as user-named
            })\
            .eq("id", str(domain_id))\
            .execute()

        if result.data:
            return {"success": True, "name": request.name}

        raise HTTPException(status_code=500, detail="Failed to update domain")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update domain {domain_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute")
async def trigger_recompute(auth: UserClient):
    """
    Manually trigger domain recomputation.

    Normally domains are recomputed automatically when deliverables change.
    This endpoint is for admin/debug purposes or after bulk operations.
    """
    try:
        from services.domain_inference import recompute_user_domains

        result = await recompute_user_domains(auth.user_id)

        return {
            "success": True,
            "changes": result
        }
    except Exception as e:
        logger.error(f"Failed to recompute domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Domain Memory Routes (Context v2)
# =============================================================================

@router.get("/{domain_id}/memories", response_model=list[MemoryResponse])
async def list_domain_memories(domain_id: UUID, auth: UserClient):
    """
    List all memories in a domain.

    For default domain, returns user-scoped memories (previously "personal" context).
    For other domains, returns domain-scoped memories.
    """
    try:
        # Verify domain ownership
        domain_result = auth.client.table("knowledge_domains")\
            .select("id, is_default")\
            .eq("id", str(domain_id))\
            .eq("user_id", auth.user_id)\
            .single()\
            .execute()

        if not domain_result.data:
            raise HTTPException(status_code=404, detail="Domain not found")

        is_default = domain_result.data["is_default"]

        if is_default:
            # Default domain: get user-scoped memories (domain_id is null or matches)
            result = auth.client.table("knowledge_entries")\
                .select("*")\
                .eq("user_id", auth.user_id)\
                .eq("is_active", True)\
                .or_(f"domain_id.is.null,domain_id.eq.{domain_id}")\
                .order("importance", desc=True)\
                .execute()
        else:
            # Non-default domain: get domain-scoped memories
            result = auth.client.table("knowledge_entries")\
                .select("*")\
                .eq("domain_id", str(domain_id))\
                .eq("is_active", True)\
                .order("importance", desc=True)\
                .execute()

        return result.data or []

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list domain memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{domain_id}/memories", response_model=MemoryResponse)
async def create_domain_memory(domain_id: UUID, memory: MemoryCreate, auth: UserClient):
    """
    Create a memory in a domain.

    For default domain, creates user-scoped memory.
    For other domains, creates domain-scoped memory.
    """
    try:
        # Verify domain ownership
        domain_result = auth.client.table("knowledge_domains")\
            .select("id, is_default")\
            .eq("id", str(domain_id))\
            .eq("user_id", auth.user_id)\
            .single()\
            .execute()

        if not domain_result.data:
            raise HTTPException(status_code=404, detail="Domain not found")

        is_default = domain_result.data["is_default"]

        # Create memory with domain_id (null for default domain = user-scoped)
        result = await create_memory_manual(
            user_id=auth.user_id,
            content=memory.content,
            db_client=auth.client,
            domain_id=None if is_default else str(domain_id),
            tags=memory.tags,
            importance=memory.importance
        )

        if not result:
            raise HTTPException(status_code=400, detail="Failed to create memory")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create domain memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))
