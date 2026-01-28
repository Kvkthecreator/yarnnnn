"""
Chat routes - Thinking Partner conversations

Endpoints:
- POST /projects/:id/chat - Send message
- GET /projects/:id/chat - Get chat history
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

router = APIRouter()


class ChatMessage(BaseModel):
    content: str
    include_context: bool = True  # Whether to include project context


class ChatResponse(BaseModel):
    id: UUID
    role: str  # user, assistant
    content: str
    created_at: str


@router.post("/projects/{project_id}/chat")
async def send_message(project_id: UUID, message: ChatMessage):
    """
    Send message to Thinking Partner.

    If include_context=True, loads project blocks as context.
    Streams response via SSE.
    """
    async def response_stream():
        # TODO: Implement with Claude/GPT streaming
        yield f"data: {{'content': 'Not implemented'}}\n\n"

    return StreamingResponse(
        response_stream(),
        media_type="text/event-stream"
    )


@router.get("/projects/{project_id}/chat")
async def get_chat_history(project_id: UUID) -> list[ChatResponse]:
    """Get chat history for project."""
    # TODO: Implement with Supabase
    raise HTTPException(status_code=501, detail="Not implemented")
