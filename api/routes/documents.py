"""
Document routes - File upload and management

ADR-008: Document Pipeline Architecture

Endpoints:
- POST /documents/upload - Upload and process a document
- GET /documents - List user's documents
- GET /documents/{id} - Get document details with stats
- GET /documents/{id}/download - Get signed download URL
- DELETE /documents/{id} - Delete document (cascades to chunks, memories)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient, get_supabase_url, get_service_client
from services.documents import process_document

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: Optional[str]
    file_size: Optional[int]
    project_id: Optional[str]
    processing_status: str
    processed_at: Optional[str]
    error_message: Optional[str]
    page_count: Optional[int]
    word_count: Optional[int]
    created_at: str


class DocumentDetailResponse(DocumentResponse):
    chunk_count: int
    memory_count: int


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    processing_status: str
    message: str


class DownloadResponse(BaseModel):
    url: str
    expires_in: int  # seconds


# =============================================================================
# UPLOAD
# =============================================================================

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    auth: UserClient,
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
):
    """
    Upload a document for processing.

    The document will be:
    1. Stored in Supabase Storage
    2. Parsed and chunked
    3. Embeddings generated
    4. Memories extracted

    Args:
        file: The file to upload (PDF, DOCX, TXT, MD)
        project_id: Optional project to scope the document to

    Returns:
        Document ID and processing status
    """
    # Validate file type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        # Try to infer from filename
        ext = file.filename.split(".")[-1].lower() if file.filename else ""
        if ext not in ("pdf", "docx", "txt", "md"):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {content_type}. Allowed: PDF, DOCX, TXT, MD"
            )
        file_type = ext
    else:
        file_type = ALLOWED_TYPES[content_type]

    # Read file content
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    if len(content) < 10:
        raise HTTPException(status_code=400, detail="File is empty or too small")

    # Validate project_id if provided
    if project_id:
        project = auth.client.table("projects").select("id").eq("id", project_id).execute()
        if not project.data:
            raise HTTPException(status_code=404, detail="Project not found")

    # Create document record
    import uuid
    document_id = str(uuid.uuid4())
    storage_path = f"{auth.user_id}/{document_id}/original.{file_type}"

    # Upload to storage using service client (user already authenticated via endpoint)
    # Storage RLS doesn't work well with user JWT auth, so we use service role
    try:
        service = get_service_client()
        storage_result = service.storage.from_("documents").upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type or f"application/{file_type}"}
        )
        # Check for storage errors in response
        if hasattr(storage_result, 'error') and storage_result.error:
            raise HTTPException(status_code=500, detail=f"Storage error: {storage_result.error}")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Storage upload error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    # Create document record
    # ADR-058: filesystem_documents doesn't have project_id or file_url columns
    doc_record = {
        "id": document_id,
        "user_id": auth.user_id,
        "filename": file.filename or f"document.{file_type}",
        "file_type": file_type,
        "file_size": len(content),
        "storage_path": storage_path,
        "processing_status": "pending",
    }

    try:
        auth.client.table("filesystem_documents").insert(doc_record).execute()
    except Exception as e:
        # Clean up storage if DB insert fails
        try:
            auth.client.storage.from_("documents").remove([storage_path])
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to create document record: {e}")

    # Process document (synchronous for MVP)
    # Use service client to bypass RLS for chunk/memory insertion
    # (user auth already verified at this point)
    service = get_service_client()
    result = await process_document(
        document_id=document_id,
        file_content=content,
        file_type=file_type,
        project_id=project_id,
        user_id=auth.user_id,
        db_client=service
    )

    status = "completed" if result.get("success") else "failed"

    return UploadResponse(
        document_id=document_id,
        filename=file.filename or f"document.{file_type}",
        processing_status=status,
        message=f"Processed: {result.get('chunks_created', 0)} chunks, {result.get('memories_extracted', 0)} memories"
        if result.get("success")
        else f"Processing failed: {result.get('error', 'Unknown error')}"
    )


# =============================================================================
# LIST
# =============================================================================

@router.get("/documents")
async def list_documents(
    auth: UserClient,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List user's documents.

    Args:
        project_id: Filter by project (null for user-scoped docs)
        status: Filter by processing_status
        limit: Max results (default 50)
        offset: Pagination offset
    """
    query = auth.client.table("filesystem_documents").select("*").eq("user_id", auth.user_id)

    if project_id:
        query = query.eq("project_id", project_id)

    if status:
        query = query.eq("processing_status", status)

    query = query.order("uploaded_at", desc=True).range(offset, offset + limit - 1)

    result = query.execute()

    return {
        "documents": [
            DocumentResponse(
                id=d["id"],
                filename=d["filename"],
                file_type=d.get("file_type"),
                file_size=d.get("file_size"),
                project_id=d.get("project_id"),
                processing_status=d.get("processing_status", "unknown"),
                processed_at=d.get("processed_at"),
                error_message=d.get("error_message"),
                page_count=d.get("page_count"),
                word_count=d.get("word_count"),
                created_at=d.get("uploaded_at"),  # ADR-058: uploaded_at replaces created_at
            )
            for d in (result.data or [])
        ],
        "total": len(result.data or []),
        "limit": limit,
        "offset": offset,
    }


# =============================================================================
# GET DETAIL
# =============================================================================

@router.get("/documents/{document_id}")
async def get_document(auth: UserClient, document_id: str):
    """
    Get document details with chunk and memory counts.
    """
    # Use the RPC function for stats
    result = auth.client.rpc(
        "get_document_with_stats",
        {"doc_id": document_id}
    ).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    d = result.data[0]

    return DocumentDetailResponse(
        id=d["id"],
        filename=d["filename"],
        file_type=d.get("file_type"),
        file_size=d.get("file_size"),
        project_id=d.get("project_id"),
        processing_status=d.get("processing_status", "unknown"),
        processed_at=d.get("processed_at"),
        error_message=d.get("error_message"),
        page_count=d.get("page_count"),
        word_count=d.get("word_count"),
        created_at=d["created_at"],
        chunk_count=d.get("chunk_count", 0),
        memory_count=d.get("memory_count", 0),
    )


# =============================================================================
# DOWNLOAD
# =============================================================================

@router.get("/documents/{document_id}/download")
async def download_document(auth: UserClient, document_id: str):
    """
    Get a signed URL to download the original document.

    Returns a URL that expires in 1 hour.
    """
    # Get document to verify ownership and get storage path
    doc = auth.client.table("filesystem_documents")\
        .select("storage_path, filename")\
        .eq("id", document_id)\
        .eq("user_id", auth.user_id)\
        .execute()

    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")

    storage_path = doc.data[0].get("storage_path")
    if not storage_path:
        raise HTTPException(status_code=404, detail="Document file not found in storage")

    # Generate signed URL (1 hour expiry) - use service client for storage
    try:
        service = get_service_client()
        signed = service.storage.from_("documents").create_signed_url(
            path=storage_path,
            expires_in=3600
        )
        return DownloadResponse(
            url=signed.get("signedURL") or signed.get("signedUrl"),
            expires_in=3600
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {e}")


# =============================================================================
# DELETE
# =============================================================================

@router.delete("/documents/{document_id}")
async def delete_document(auth: UserClient, document_id: str):
    """
    Delete a document and all associated data.

    Cascades to:
    - Chunks (via FK cascade)
    - Storage file
    - Memories are NOT deleted (they persist as extracted knowledge)
    """
    # Get document to verify ownership and get storage path
    doc = auth.client.table("filesystem_documents")\
        .select("storage_path")\
        .eq("id", document_id)\
        .eq("user_id", auth.user_id)\
        .execute()

    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")

    storage_path = doc.data[0].get("storage_path")

    # Delete from storage (if exists) - use service client for storage
    if storage_path:
        try:
            service = get_service_client()
            service.storage.from_("documents").remove([storage_path])
        except Exception as e:
            print(f"Warning: Failed to delete storage file: {e}")

    # Delete document record (chunks cascade via FK)
    auth.client.table("filesystem_documents").delete().eq("id", document_id).execute()

    return {"success": True, "message": "Document deleted"}
