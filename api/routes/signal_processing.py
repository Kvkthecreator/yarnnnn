"""
Signal Processing routes - Manual trigger for signal-emergent deliverables

ADR-068: Signal-Emergent Deliverables

Endpoints:
- POST /signal-processing/trigger - Manually trigger signal processing
"""

import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class TriggerSignalProcessingRequest(BaseModel):
    signals_filter: Optional[Literal["all", "calendar_only", "non_calendar"]] = "all"


class SignalActionSummary(BaseModel):
    action_type: str  # create_signal_emergent | trigger_existing | no_action
    deliverable_id: Optional[str] = None
    deliverable_type: str
    title: str
    signal_reference: Optional[str] = None  # event_id or thread_id
    advanced_from: Optional[str] = None  # For trigger_existing
    advanced_to: Optional[str] = None    # For trigger_existing


class TriggerSignalProcessingResponse(BaseModel):
    status: Literal["completed", "rate_limited", "no_platforms"]
    signals_detected: int
    actions_taken: list[SignalActionSummary] = Field(default_factory=list)
    deliverables_created: int = 0
    existing_triggered: int = 0
    last_run_at: Optional[str] = None
    next_eligible_at: Optional[str] = None
    message: Optional[str] = None


# =============================================================================
# Manual Signal Processing Trigger
# =============================================================================

@router.post("/signal-processing/trigger")
async def trigger_signal_processing(
    request: TriggerSignalProcessingRequest,
    user: UserClient,
) -> TriggerSignalProcessingResponse:
    """
    Manually trigger signal processing for the authenticated user.

    This endpoint runs the same signal processing logic as the hourly/daily cron,
    but on-demand. Useful for:
    - Testing after reconnecting OAuth platforms
    - Immediate signal discovery after scheduling meetings
    - Debugging platform connection issues

    Rate limiting: 5 minute cooldown between manual triggers.
    """
    user_id = user.user_id
    supabase = user.client
    now = datetime.now(timezone.utc)

    # =============================================================================
    # Rate Limiting Check (5 minute cooldown)
    # =============================================================================
    try:
        # Check last manual trigger from user_notification_preferences
        prefs_result = (
            supabase.table("user_notification_preferences")
            .select("signal_last_manual_trigger_at")
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if prefs_result.data and prefs_result.data.get("signal_last_manual_trigger_at"):
            last_trigger = datetime.fromisoformat(
                prefs_result.data["signal_last_manual_trigger_at"].replace("Z", "+00:00")
            )
            cooldown_period = timedelta(minutes=5)
            next_eligible = last_trigger + cooldown_period

            if now < next_eligible:
                seconds_remaining = int((next_eligible - now).total_seconds())
                return TriggerSignalProcessingResponse(
                    status="rate_limited",
                    signals_detected=0,
                    last_run_at=last_trigger.isoformat(),
                    next_eligible_at=next_eligible.isoformat(),
                    message=f"Please wait {seconds_remaining} seconds before triggering again"
                )

    except Exception as e:
        logger.warning(f"[SIGNAL_TRIGGER] Rate limit check failed for {user_id}: {e}")
        # Continue anyway — don't block on rate limit check failure

    # =============================================================================
    # Platform Connection Check
    # =============================================================================
    try:
        connections_result = (
            supabase.table("platform_connections")
            .select("platform, status")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )

        if not connections_result.data:
            return TriggerSignalProcessingResponse(
                status="no_platforms",
                signals_detected=0,
                message="No active platform connections. Please connect Google Calendar or Gmail in Settings."
            )

    except Exception as e:
        logger.error(f"[SIGNAL_TRIGGER] Platform check failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check platform connections")

    # =============================================================================
    # Signal Processing Execution
    # =============================================================================
    try:
        from services.signal_extraction import extract_signal_summary
        from services.signal_processing import process_signal, execute_signal_actions
        from services.activity_log import get_recent_activity

        # Extract signals with requested filter
        signal_summary = await extract_signal_summary(
            supabase, user_id, signals_filter=request.signals_filter
        )

        if not signal_summary.has_signals:
            return TriggerSignalProcessingResponse(
                status="completed",
                signals_detected=0,
                message="No signals detected from your connected platforms"
            )

        # Fetch context for LLM reasoning
        user_context_result = (
            supabase.table("user_context")
            .select("key, value")
            .eq("user_id", user_id)
            .limit(20)
            .execute()
        )
        user_context = user_context_result.data or []

        recent_activity = await get_recent_activity(
            client=supabase,
            user_id=user_id,
            limit=10,
            days=7,
        )

        # ADR-069: Fetch Layer 4 content for signal reasoning
        existing_deliverables_raw = (
            supabase.table("deliverables")
            .select("""
                id, title, deliverable_type, next_run_at, status,
                deliverable_versions!inner(
                    final_content,
                    draft_content,
                    created_at,
                    status
                )
            """)
            .eq("user_id", user_id)
            .in_("status", ["active", "paused"])
            .order("deliverable_versions(created_at)", desc=True)
            .execute()
        )

        # Extract most recent version per deliverable
        existing_deliverables = []
        for d in (existing_deliverables_raw.data or []):
            versions = d.get("deliverable_versions", [])
            recent_version = versions[0] if versions else None
            existing_deliverables.append({
                "id": d["id"],
                "title": d["title"],
                "deliverable_type": d["deliverable_type"],
                "next_run_at": d.get("next_run_at"),
                "status": d["status"],
                "recent_content": (
                    recent_version.get("final_content") or
                    recent_version.get("draft_content")
                ) if recent_version else None,
                "recent_version_date": recent_version.get("created_at") if recent_version else None,
            })

        # Phase 1: Signal reasoning (orchestration)
        processing_result = await process_signal(
            client=supabase,
            user_id=user_id,
            signal_summary=signal_summary,
            user_context=user_context,
            recent_activity=recent_activity,
            existing_deliverables=existing_deliverables,
        )

        # Phase 2: Execute actions (selective artifact creation)
        deliverables_created = 0
        existing_triggered = 0
        action_summaries = []

        if processing_result.actions:
            deliverables_created = await execute_signal_actions(
                client=supabase,
                user_id=user_id,
                result=processing_result,
            )

            # Build action summaries for response
            for action in processing_result.actions:
                signal_ref = (
                    action.signal_context.get("event_id") or
                    action.signal_context.get("thread_id")
                )

                if action.action_type == "create_signal_emergent":
                    # Find the created deliverable ID (it was created in execute_signal_actions)
                    # We'll need to query for it since we don't return it from execute
                    recent_deliverable = (
                        supabase.table("deliverables")
                        .select("id")
                        .eq("user_id", user_id)
                        .eq("origin", "signal_emergent")
                        .eq("deliverable_type", action.deliverable_type)
                        .order("created_at", desc=True)
                        .limit(1)
                        .execute()
                    )
                    deliverable_id = recent_deliverable.data[0]["id"] if recent_deliverable.data else None

                    action_summaries.append(SignalActionSummary(
                        action_type=action.action_type,
                        deliverable_id=deliverable_id,
                        deliverable_type=action.deliverable_type,
                        title=action.title,
                        signal_reference=signal_ref,
                    ))

                elif action.action_type == "trigger_existing":
                    existing_triggered += 1

                    # Get the updated next_run_at
                    updated_deliverable = (
                        supabase.table("deliverables")
                        .select("next_run_at")
                        .eq("id", action.trigger_deliverable_id)
                        .single()
                        .execute()
                    )

                    action_summaries.append(SignalActionSummary(
                        action_type=action.action_type,
                        deliverable_id=action.trigger_deliverable_id,
                        deliverable_type=action.deliverable_type,
                        title=action.title,
                        signal_reference=signal_ref,
                        advanced_to=updated_deliverable.data.get("next_run_at") if updated_deliverable.data else None,
                    ))

        # Update last manual trigger timestamp
        try:
            supabase.table("user_notification_preferences").upsert({
                "user_id": user_id,
                "signal_last_manual_trigger_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }, on_conflict="user_id").execute()
        except Exception as e:
            logger.warning(f"[SIGNAL_TRIGGER] Failed to update last trigger timestamp: {e}")

        total_signals = (
            signal_summary.calendar_signals_count +
            signal_summary.silence_signals_count
        )

        return TriggerSignalProcessingResponse(
            status="completed",
            signals_detected=total_signals,
            actions_taken=action_summaries,
            deliverables_created=deliverables_created,
            existing_triggered=existing_triggered,
            last_run_at=now.isoformat(),
            message=f"Processed {total_signals} signal(s): created {deliverables_created} deliverable(s), triggered {existing_triggered} existing"
        )

    except Exception as e:
        logger.error(f"[SIGNAL_TRIGGER] Signal processing failed for {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Signal processing failed: {str(e)}"
        )
