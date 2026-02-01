"""
Deliverable Pipeline Execution Service

ADR-018: Recurring Deliverables Product Pivot

Implements the 3-step chained pipeline:
1. Gather - Research agent pulls latest context from sources
2. Synthesize - Content agent produces the deliverable
3. Stage - Format and notify user for review

Each step creates a work ticket with dependency chaining.
"""

import logging
import json
from datetime import datetime
from typing import Optional

from services.work_execution import execute_work_ticket

logger = logging.getLogger(__name__)


async def execute_deliverable_pipeline(
    client,
    user_id: str,
    deliverable_id: str,
    version_number: int,
) -> dict:
    """
    Execute the full deliverable pipeline.

    Creates a new version, runs gather → synthesize → stage,
    and updates the deliverable with last_run_at.

    Args:
        client: Supabase client
        user_id: User UUID
        deliverable_id: Deliverable UUID
        version_number: Version number to create

    Returns:
        Pipeline result with version_id, status, and message
    """
    logger.info(f"[PIPELINE] Starting: deliverable={deliverable_id}, version={version_number}")

    # Get deliverable details
    deliverable_result = (
        client.table("deliverables")
        .select("*")
        .eq("id", deliverable_id)
        .single()
        .execute()
    )

    if not deliverable_result.data:
        return {"success": False, "error": "Deliverable not found"}

    deliverable = deliverable_result.data
    project_id = deliverable.get("project_id")

    # Create version record
    version_result = (
        client.table("deliverable_versions")
        .insert({
            "deliverable_id": deliverable_id,
            "version_number": version_number,
            "status": "generating",
        })
        .execute()
    )

    if not version_result.data:
        return {"success": False, "error": "Failed to create version"}

    version = version_result.data[0]
    version_id = version["id"]

    try:
        # Step 1: Gather
        logger.info(f"[PIPELINE] Step 1: Gather")
        gather_result = await execute_gather_step(
            client=client,
            user_id=user_id,
            project_id=project_id,
            deliverable=deliverable,
            version_id=version_id,
        )

        if not gather_result.get("success"):
            await update_version_status(client, version_id, "failed")
            return {
                "success": False,
                "version_id": version_id,
                "status": "failed",
                "message": f"Gather step failed: {gather_result.get('error')}",
            }

        gathered_context = gather_result.get("output", "")

        # Step 2: Synthesize
        logger.info(f"[PIPELINE] Step 2: Synthesize")
        synthesize_result = await execute_synthesize_step(
            client=client,
            user_id=user_id,
            project_id=project_id,
            deliverable=deliverable,
            version_id=version_id,
            gathered_context=gathered_context,
            gather_work_id=gather_result.get("work_id"),
        )

        if not synthesize_result.get("success"):
            await update_version_status(client, version_id, "failed")
            return {
                "success": False,
                "version_id": version_id,
                "status": "failed",
                "message": f"Synthesize step failed: {synthesize_result.get('error')}",
            }

        draft_content = synthesize_result.get("output", "")

        # Step 3: Stage
        logger.info(f"[PIPELINE] Step 3: Stage")
        stage_result = await execute_stage_step(
            client=client,
            version_id=version_id,
            draft_content=draft_content,
            deliverable=deliverable,
        )

        # Update deliverable last_run_at
        client.table("deliverables").update({
            "last_run_at": datetime.utcnow().isoformat(),
        }).eq("id", deliverable_id).execute()

        logger.info(f"[PIPELINE] Complete: version={version_id}, status=staged")

        return {
            "success": True,
            "version_id": version_id,
            "status": "staged",
            "message": "Deliverable ready for review",
        }

    except Exception as e:
        logger.error(f"[PIPELINE] Error: {e}")
        await update_version_status(client, version_id, "failed")
        return {
            "success": False,
            "version_id": version_id,
            "status": "failed",
            "message": str(e),
        }


async def execute_gather_step(
    client,
    user_id: str,
    project_id: str,
    deliverable: dict,
    version_id: str,
) -> dict:
    """
    Step 1: Gather context from sources.

    Uses research agent to pull latest information from configured sources.
    Output is saved as a memory with source_type='agent_output'.
    """
    sources = deliverable.get("sources", [])
    title = deliverable.get("title", "Deliverable")

    # Build gather prompt
    source_descriptions = []
    for source in sources:
        source_type = source.get("type", "description")
        value = source.get("value", "")
        label = source.get("label", "")

        if source_type == "url":
            source_descriptions.append(f"- Web source: {value}")
        elif source_type == "document":
            source_descriptions.append(f"- Document: {label or value}")
        else:
            source_descriptions.append(f"- Context: {value}")

    sources_text = "\n".join(source_descriptions) if source_descriptions else "No specific sources configured"

    gather_prompt = f"""Gather the latest context and information for producing: {title}

Description: {deliverable.get('description', 'No description provided')}

Configured sources:
{sources_text}

Your task:
1. Review and synthesize any available information from the sources
2. Identify key updates, changes, or new data since the last delivery
3. Note any gaps or missing information that might be needed
4. Summarize the gathered context in a structured format

Output a comprehensive context summary that will be used to produce the deliverable."""

    # Create work ticket
    ticket_data = {
        "task": gather_prompt,
        "agent_type": "research",
        "project_id": project_id,
        "parameters": json.dumps({
            "deliverable_id": deliverable["id"],
            "step": "gather",
        }),
        "status": "pending",
        "deliverable_id": deliverable["id"],
        "deliverable_version_id": version_id,
        "pipeline_step": "gather",
        "chain_output_as_memory": True,
    }

    ticket_result = client.table("work_tickets").insert(ticket_data).execute()

    if not ticket_result.data:
        return {"success": False, "error": "Failed to create gather work ticket"}

    ticket_id = ticket_result.data[0]["id"]

    # Execute the work
    result = await execute_work_ticket(
        client=client,
        user_id=user_id,
        ticket_id=ticket_id,
    )

    if result.get("success"):
        # Save output as memory
        output_content = ""
        outputs = result.get("outputs", [])
        if outputs:
            output_content = outputs[0].get("content", "")

        if output_content:
            await save_as_memory(
                client=client,
                user_id=user_id,
                project_id=project_id,
                content=f"[GATHER] {output_content}",
                source_type="agent_output",
                tags=["pipeline:gather", f"deliverable:{deliverable['id']}"],
            )

        return {
            "success": True,
            "work_id": ticket_id,
            "output": output_content,
        }

    return {
        "success": False,
        "error": result.get("error", "Gather execution failed"),
    }


async def execute_synthesize_step(
    client,
    user_id: str,
    project_id: str,
    deliverable: dict,
    version_id: str,
    gathered_context: str,
    gather_work_id: Optional[str] = None,
) -> dict:
    """
    Step 2: Synthesize the deliverable content.

    Uses content agent with gathered context, template structure,
    recipient context, and learned preferences from past versions.
    """
    title = deliverable.get("title", "Deliverable")
    template = deliverable.get("template_structure", {})
    recipient = deliverable.get("recipient_context", {})

    # Get past versions for preference learning
    past_versions = await get_past_versions_context(client, deliverable["id"])

    # Build synthesis prompt
    sections_text = ""
    if template.get("sections"):
        sections_text = "Expected sections:\n" + "\n".join(f"- {s}" for s in template["sections"])

    recipient_text = ""
    if recipient:
        recipient_parts = []
        if recipient.get("name"):
            recipient_parts.append(f"Recipient: {recipient['name']}")
        if recipient.get("role"):
            recipient_parts.append(f"Role: {recipient['role']}")
        if recipient.get("priorities"):
            recipient_parts.append(f"Key priorities: {', '.join(recipient['priorities'])}")
        recipient_text = "\n".join(recipient_parts)

    length_guidance = template.get("typical_length", "appropriate length")
    tone_guidance = template.get("tone", "professional")

    synthesize_prompt = f"""Produce the following deliverable: {title}

{recipient_text}

{sections_text}

Tone: {tone_guidance}
Length: {length_guidance}

GATHERED CONTEXT:
{gathered_context}

{past_versions}

Based on the gathered context and the guidelines above, produce the complete deliverable.
Make it ready for review and delivery to the recipient."""

    # Create work ticket with dependency
    ticket_data = {
        "task": synthesize_prompt,
        "agent_type": "content",
        "project_id": project_id,
        "parameters": json.dumps({
            "deliverable_id": deliverable["id"],
            "step": "synthesize",
        }),
        "status": "pending",
        "deliverable_id": deliverable["id"],
        "deliverable_version_id": version_id,
        "pipeline_step": "synthesize",
        "depends_on_work_id": gather_work_id,
        "chain_output_as_memory": True,
    }

    ticket_result = client.table("work_tickets").insert(ticket_data).execute()

    if not ticket_result.data:
        return {"success": False, "error": "Failed to create synthesize work ticket"}

    ticket_id = ticket_result.data[0]["id"]

    # Execute the work
    result = await execute_work_ticket(
        client=client,
        user_id=user_id,
        ticket_id=ticket_id,
    )

    if result.get("success"):
        output_content = ""
        outputs = result.get("outputs", [])
        if outputs:
            output_content = outputs[0].get("content", "")

        if output_content:
            await save_as_memory(
                client=client,
                user_id=user_id,
                project_id=project_id,
                content=f"[SYNTHESIZE] {output_content[:500]}...",  # Truncate for memory
                source_type="agent_output",
                tags=["pipeline:synthesize", f"deliverable:{deliverable['id']}"],
            )

        return {
            "success": True,
            "work_id": ticket_id,
            "output": output_content,
        }

    return {
        "success": False,
        "error": result.get("error", "Synthesize execution failed"),
    }


async def execute_stage_step(
    client,
    version_id: str,
    draft_content: str,
    deliverable: dict,
) -> dict:
    """
    Step 3: Stage the deliverable for review.

    Updates version with draft content and sets status to 'staged'.
    Triggers notification to user (via existing email infrastructure).
    """
    # Update version
    update_result = (
        client.table("deliverable_versions")
        .update({
            "draft_content": draft_content,
            "status": "staged",
            "staged_at": datetime.utcnow().isoformat(),
        })
        .eq("id", version_id)
        .execute()
    )

    if not update_result.data:
        return {"success": False, "error": "Failed to stage version"}

    # TODO: Send staging notification email
    # This will use the existing email infrastructure
    # For now, just log it
    logger.info(f"[STAGE] Version {version_id} staged for review")

    return {"success": True}


async def get_past_versions_context(client, deliverable_id: str) -> str:
    """
    Get context from past versions including feedback patterns.

    Returns a formatted string with learned preferences from edit history.
    """
    # Get recent approved versions with edits
    versions_result = (
        client.table("deliverable_versions")
        .select("version_number, edit_categories, edit_distance_score, feedback_notes")
        .eq("deliverable_id", deliverable_id)
        .eq("status", "approved")
        .order("version_number", desc=True)
        .limit(5)
        .execute()
    )

    versions = versions_result.data or []

    if not versions:
        return ""

    # Aggregate feedback patterns
    patterns = []
    for v in versions:
        categories = v.get("edit_categories", {})
        if categories:
            if categories.get("additions"):
                patterns.append(f"User added: {', '.join(categories['additions'][:3])}")
            if categories.get("deletions"):
                patterns.append(f"User removed: {', '.join(categories['deletions'][:3])}")

        if v.get("feedback_notes"):
            patterns.append(f"Feedback: {v['feedback_notes']}")

    if not patterns:
        return ""

    return f"""
LEARNED PREFERENCES (from past versions):
{chr(10).join(f'- {p}' for p in patterns[:10])}

Apply these preferences when producing this version."""


async def save_as_memory(
    client,
    user_id: str,
    project_id: str,
    content: str,
    source_type: str = "agent_output",
    tags: Optional[list] = None,
) -> Optional[str]:
    """
    Save content as a project memory.
    """
    memory_data = {
        "user_id": user_id,
        "project_id": project_id,
        "content": content,
        "source_type": source_type,
        "importance": 0.8,
        "tags": tags or [],
    }

    result = client.table("memories").insert(memory_data).execute()

    if result.data:
        return result.data[0]["id"]
    return None


async def update_version_status(client, version_id: str, status: str):
    """Update version status."""
    client.table("deliverable_versions").update({
        "status": status,
    }).eq("id", version_id).execute()
