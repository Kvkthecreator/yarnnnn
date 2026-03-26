"""
UpdateSharedContext Primitive — ADR-144: Inference-First Shared Context

Single primitive for updating workspace shared context (IDENTITY.md, BRAND.md).
TP gathers sources (text, docs, URLs, platform content) then calls this.
Inference generates rich markdown and writes to workspace file.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


UPDATE_SHARED_CONTEXT_TOOL = {
    "name": "UpdateSharedContext",
    "description": """Update shared workspace context (identity or brand) using inference.

Call this when the user wants to update their identity or brand. You gather the
source material first (from their message, uploaded documents, web search results,
or platform content), then pass it here. Inference generates rich markdown and
writes to the workspace file.

Examples:
- User says "Update my identity — I'm Sarah, VP Eng at Acme" → call with target="identity", text="I'm Sarah..."
- User says "Update my brand from acme.com" → first WebSearch acme.com, then call with target="brand", url_contents=[{url, content}]
- User says "Update my identity from my pitch deck" → read the document, then call with target="identity", document_contents=[{filename, content}]

The inference merges with existing content — it won't lose information already in the file.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "enum": ["identity", "brand"],
                "description": "Which workspace file to update: 'identity' (IDENTITY.md) or 'brand' (BRAND.md)"
            },
            "text": {
                "type": "string",
                "description": "Direct text from user's message — their description, context, or instructions"
            },
            "document_contents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "content": {"type": "string"}
                    }
                },
                "description": "Content from uploaded documents [{filename, content}]"
            },
            "url_contents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "content": {"type": "string"}
                    }
                },
                "description": "Content from web pages [{url, content}]"
            },
        },
        "required": ["target"]
    }
}


async def handle_update_shared_context(auth: Any, input: dict) -> dict:
    """Handle UpdateSharedContext primitive.

    Reads existing workspace file, runs inference with provided sources,
    writes updated content back.
    """
    from services.context_inference import infer_shared_context
    from services.workspace import UserMemory

    target = input.get("target")
    if target not in ("identity", "brand"):
        return {"success": False, "error": "invalid_target", "message": "target must be 'identity' or 'brand'"}

    text = input.get("text", "")
    document_contents = input.get("document_contents", [])
    url_contents = input.get("url_contents", [])

    filename = "IDENTITY.md" if target == "identity" else "BRAND.md"

    try:
        um = UserMemory(auth.client, auth.user_id)

        # Read existing content for merge
        existing = await um.read(filename)

        # Run inference
        new_content = await infer_shared_context(
            target=target,
            text=text,
            document_contents=document_contents,
            url_contents=url_contents,
            existing_content=existing or "",
        )

        if not new_content or not new_content.strip():
            return {"success": False, "error": "inference_empty", "message": "Inference produced no content — try providing more detail"}

        # Write to workspace
        ok = await um.write(filename, new_content, summary=f"{target.capitalize()} updated via inference")
        if not ok:
            return {"success": False, "error": "write_failed", "message": f"Failed to write {filename}"}

        logger.info(f"[SHARED_CONTEXT] Updated {filename} ({len(new_content)} chars)")
        return {
            "success": True,
            "target": target,
            "filename": filename,
            "content": new_content,
            "message": f"Updated {filename} successfully",
        }

    except Exception as e:
        logger.error(f"[SHARED_CONTEXT] Failed to update {target}: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}
