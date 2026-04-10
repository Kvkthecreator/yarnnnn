from __future__ import annotations

"""
Delivery Service - ADR-028, ADR-031 Phase 6, ADR-040, ADR-066

Delivery orchestration for destination-first agents.

This service handles:
1. Orchestrating delivery via exporters
2. Tracking delivery status on versions
3. Retry logic for failed deliveries
4. Multi-destination delivery for synthesizers (ADR-031 Phase 6)
5. Sending notifications on delivery events (ADR-040)

ADR-066: All agents auto-deliver immediately after generation.
Governance was removed - delivery is always automatic when destination is set.
"""

import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any

from integrations.core.types import ExportResult, ExportStatus
from integrations.core.tokens import get_token_manager
from integrations.exporters import get_exporter_registry, ExporterContext
from services.schedule_utils import (
    format_datetime_for_timezone,
    get_user_timezone,
)

logger = logging.getLogger(__name__)


@dataclass
class MultiDestinationResult:
    """Result of delivering to multiple destinations."""
    total_destinations: int
    succeeded: int
    failed: int
    results: list[dict]  # [{destination_index, platform, status, external_id, error}]
    all_succeeded: bool


class DeliveryService:
    """
    Handles delivery of approved versions to configured destinations.

    Usage:
        service = DeliveryService(supabase_client)

        # Check if delivery should auto-trigger
        if service.should_auto_deliver(agent):
            result = await service.deliver_version(version_id, user_id)
    """

    def __init__(self, client):
        """
        Initialize the delivery service.

        Args:
            client: Supabase client (user or service)
        """
        self.client = client
        self.registry = get_exporter_registry()
        self.token_manager = get_token_manager()

    def should_auto_deliver(self, agent: dict[str, Any]) -> bool:
        """
        Determine if an agent should auto-deliver.

        ADR-066: All agents auto-deliver when destination is set.

        Args:
            agent: The agent record

        Returns:
            True if auto-delivery should occur
        """
        destination = None  # Column dropped — destination no longer on agents table

        # Must have destination configured
        if not destination:
            return False

        # ADR-066: All agents auto-deliver
        return True

    def get_style_context(self, agent: dict[str, Any]) -> Optional[str]:
        """
        Infer style context from destination platform.

        ADR-028: If destination is set, use platform as style context.
        This lets content generation adapt to the destination format.

        Args:
            agent: The agent record

        Returns:
            Style context string, or None if no destination
        """
        destination = None  # Column dropped — destination no longer on agents table
        if not destination:
            return None

        platform = destination.get("platform")
        if not platform:
            return None

        exporter = self.registry.get(platform)
        if exporter:
            return exporter.infer_style_context()

        return platform

    async def deliver_version(
        self,
        version_id: str,
        user_id: str,
        retry_count: int = 0
    ) -> ExportResult:
        """
        Deliver an approved version to its destination.

        Args:
            version_id: The agent version ID
            user_id: The user ID (for auth)
            retry_count: Number of retries attempted

        Returns:
            ExportResult with delivery status
        """
        try:
            # 1. Get version and agent
            version = self.client.table("agent_runs").select(
                "id, agent_id, final_content, status, delivery_status, version_number"
            ).eq("id", version_id).single().execute()

            if not version.data:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message="Version not found"
                )

            # 2. Get agent (identity only — destination/mode now on tasks)
            agent = self.client.table("agents").select(
                "id, title, user_id, scope, role"
            ).eq("id", version.data["agent_id"]).single().execute()

            if not agent.data:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message="Agent not found"
                )

            # 3. Delivery is now per-task (ADR-138) — this legacy path is unused
            # Delivery flows through deliver_from_output_folder() which reads TASK.md
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="Legacy deliver_version path — use deliver_from_output_folder() instead"
                )

            # 4. Get exporter
            exporter = self.registry.get(platform)
            if not exporter:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message=f"No exporter for platform: {platform}"
                )

            # 5. Get auth context (if required)
            context = await self._get_exporter_context(user_id, platform)
            if exporter.requires_auth and not context:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message=f"No {platform} integration connected"
                )

            # 6. Mark delivery as in-progress
            self._update_delivery_status(version_id, "delivering")

            # 7. Deliver
            content = version.data.get("final_content") or version.data.get("draft_content", "")
            title = agent.data.get("title", "YARNNN Agent")

            result = await exporter.deliver(
                destination=destination,
                content=content,
                title=title,
                metadata={
                    "agent_id": agent.data["id"],
                    "version_id": version_id,
                    "version_number": version.data.get("version_number"),
                    "role": agent.data.get("role"),
                    "mode": None,  # ADR-138: mode is on tasks, not agents
                    "retry_count": retry_count,
                },
                context=context
            )

            # 8. Update delivery status and send notifications (ADR-040)
            if result.status == ExportStatus.SUCCESS:
                self._update_delivery_status(
                    version_id,
                    "delivered",
                    external_id=result.external_id,
                    external_url=result.external_url
                )
                self._log_export(
                    version_id=version_id,
                    user_id=user_id,
                    platform=platform,
                    destination=destination,
                    result=result
                )
                # ADR-040: Notify on delivery — notification service handles
                # email-platform skip internally (content email IS the notification)
                await self._notify_delivered(
                    user_id=user_id,
                    agent_id=agent.data["id"],
                    title=title,
                    platform=platform,
                    target=destination.get("target"),
                    external_url=result.external_url,
                )
            else:
                self._update_delivery_status(
                    version_id,
                    "failed",
                    error=result.error_message
                )
                # ADR-040: Send failure notification
                await self._notify_failed(
                    user_id=user_id,
                    agent_id=agent.data["id"],
                    title=title,
                    error=result.error_message or "Unknown error",
                )

            logger.info(
                f"[DELIVERY] Version {version_id} to {platform}: {result.status.value}"
            )

            return result

        except Exception as e:
            logger.error(f"[DELIVERY] Failed for version {version_id}: {e}")
            self._update_delivery_status(version_id, "failed", error=str(e))
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    async def _get_exporter_context(
        self,
        user_id: str,
        platform: str
    ) -> Optional[ExporterContext]:
        """Get auth context for an exporter."""
        # Platforms that don't need user OAuth
        if platform in ("download", "email"):
            return ExporterContext(
                user_id=user_id,
                access_token="",
                metadata={}
            )

        # ADR-131: Only Slack and Notion remain — no Google/Gmail alias resolution needed
        lookup_candidates = [platform]

        try:
            # Get user's integration — try each candidate
            integration = None
            for candidate in lookup_candidates:
                try:
                    result = self.client.table("platform_connections").select(
                        "credentials_encrypted, refresh_token_encrypted, metadata, status"
                    ).eq("user_id", user_id).eq("platform", candidate).single().execute()
                    if result.data and result.data["status"] == "active":
                        integration = result
                        break
                except Exception:
                    continue

            if not integration or not integration.data:
                return None

            # Decrypt token
            access_token = self.token_manager.decrypt(
                integration.data["credentials_encrypted"]
            )

            refresh_token = None
            if integration.data.get("refresh_token_encrypted"):
                refresh_token = self.token_manager.decrypt(
                    integration.data["refresh_token_encrypted"]
                )

            return ExporterContext(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                metadata=integration.data.get("metadata", {}) or {}
            )

        except Exception as e:
            logger.error(f"[DELIVERY] Failed to get context for {platform}: {e}")
            return None

    def _update_delivery_status(
        self,
        version_id: str,
        status: str,
        external_id: Optional[str] = None,
        external_url: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Update delivery status on a version."""
        update = {
            "delivery_status": status,
            "delivery_error": error
        }

        if external_id:
            update["delivery_external_id"] = external_id
        if external_url:
            update["delivery_external_url"] = external_url
        if status == "delivered":
            update["delivered_at"] = datetime.now(timezone.utc).isoformat()

        self.client.table("agent_runs").update(update).eq(
            "id", version_id
        ).execute()

    def _log_export(
        self,
        version_id: str,
        user_id: str,
        platform: str,
        destination: dict[str, Any],
        result: ExportResult
    ) -> None:
        """Log export to export_log table."""
        try:
            self.client.table("export_log").insert({
                "agent_run_id": version_id,
                "user_id": user_id,
                "provider": platform,
                "destination": destination,
                "status": result.status.value,
                "external_id": result.external_id,
                "external_url": result.external_url,
                "error_message": result.error_message,
                "completed_at": datetime.now(timezone.utc).isoformat() if result.status == ExportStatus.SUCCESS else None
            }).execute()
        except Exception as e:
            logger.warning(f"[DELIVERY] Failed to log export: {e}")

    # =========================================================================
    # ADR-040: Notification Helpers
    # =========================================================================

    async def _notify_delivered(
        self,
        user_id: str,
        agent_id: str,
        title: str,
        platform: str,
        target: Optional[str],
        external_url: Optional[str],
    ) -> None:
        """Send notification when agent is delivered."""
        try:
            from services.notifications import notify_agent_delivered
            from services.supabase import get_service_client
            destination_str = f"{platform}"
            if target:
                destination_str += f" ({target})"
            await notify_agent_delivered(
                db_client=get_service_client(),
                user_id=user_id,
                agent_id=agent_id,
                agent_title=title,
                destination=destination_str,
                external_url=external_url,
                delivery_platform=platform,
            )
        except Exception as e:
            logger.warning(f"[DELIVERY] Failed to send delivery notification: {e}")

    async def _notify_failed(
        self,
        user_id: str,
        agent_id: str,
        title: str,
        error: str,
    ) -> None:
        """Send notification when delivery fails."""
        try:
            from services.notifications import notify_agent_failed
            from services.supabase import get_service_client
            await notify_agent_failed(
                db_client=get_service_client(),
                user_id=user_id,
                agent_id=agent_id,
                agent_title=title,
                error=error,
            )
        except Exception as e:
            logger.warning(f"[DELIVERY] Failed to send failure notification: {e}")

    # =========================================================================
    # ADR-031 Phase 6: Multi-Destination Delivery
    # =========================================================================

    async def deliver_to_multiple_destinations(
        self,
        version_id: str,
        user_id: str,
        destinations: list[dict[str, Any]],
    ) -> MultiDestinationResult:
        """
        Deliver an approved version to multiple destinations.

        Used by cross-platform synthesizers to output to multiple platforms
        (e.g., Slack AND email) from a single generation.

        Args:
            version_id: The agent version ID
            user_id: The user ID (for auth)
            destinations: List of destination configs

        Returns:
            MultiDestinationResult with per-destination status
        """
        if not destinations:
            return MultiDestinationResult(
                total_destinations=0,
                succeeded=0,
                failed=0,
                results=[],
                all_succeeded=True,
            )

        # Get version content
        version = self.client.table("agent_runs").select(
            "id, agent_id, final_content, draft_content"
        ).eq("id", version_id).single().execute()

        if not version.data:
            return MultiDestinationResult(
                total_destinations=len(destinations),
                succeeded=0,
                failed=len(destinations),
                results=[{"error": "Version not found"}],
                all_succeeded=False,
            )

        # Get agent title
        agent = self.client.table("agents").select(
            "id, title, scope, role, mode"
        ).eq("id", version.data["agent_id"]).single().execute()

        content = version.data.get("final_content") or version.data.get("draft_content", "")
        title = agent.data.get("title", "YARNNN Agent") if agent.data else "Agent"
        platform_variant = None  # Was agents.platform_variant column, dropped in migration 113

        results = []
        succeeded = 0
        failed = 0

        for idx, destination in enumerate(destinations):
            platform = destination.get("platform")
            if not platform:
                results.append({
                    "destination_index": idx,
                    "platform": "unknown",
                    "status": "failed",
                    "error": "No platform specified",
                })
                failed += 1
                continue

            # Get exporter
            exporter = self.registry.get(platform)
            if not exporter:
                results.append({
                    "destination_index": idx,
                    "platform": platform,
                    "status": "failed",
                    "error": f"No exporter for platform: {platform}",
                })
                failed += 1
                continue

            # Get auth context
            context = await self._get_exporter_context(user_id, platform)
            if exporter.requires_auth and not context:
                results.append({
                    "destination_index": idx,
                    "platform": platform,
                    "status": "failed",
                    "error": f"No {platform} integration connected",
                })
                failed += 1
                continue

            try:
                # Deliver to this destination
                result = await exporter.deliver(
                    destination=destination,
                    content=content,
                    title=title,
                    metadata={
                        "agent_id": version.data["agent_id"],
                        "version_id": version_id,
                        "version_number": version.data.get("version_number"),
                        "role": agent.data.get("role") if agent.data else None,
                        "mode": None,  # ADR-138: mode is on tasks, not agents
                        "destination_index": idx,
                        "platform_variant": platform_variant,
                    },
                    context=context,
                )

                if result.status == ExportStatus.SUCCESS:
                    results.append({
                        "destination_index": idx,
                        "platform": platform,
                        "target": destination.get("target"),
                        "status": "delivered",
                        "external_id": result.external_id,
                        "external_url": result.external_url,
                    })
                    succeeded += 1

                    # Log to destination_delivery_log
                    self._log_destination_delivery(
                        version_id=version_id,
                        agent_id=version.data["agent_id"],
                        user_id=user_id,
                        destination_index=idx,
                        destination=destination,
                        result=result,
                    )
                else:
                    results.append({
                        "destination_index": idx,
                        "platform": platform,
                        "target": destination.get("target"),
                        "status": "failed",
                        "error": result.error_message,
                    })
                    failed += 1

            except Exception as e:
                logger.error(f"[DELIVERY] Failed for destination {idx} ({platform}): {e}")
                results.append({
                    "destination_index": idx,
                    "platform": platform,
                    "status": "failed",
                    "error": str(e),
                })
                failed += 1

        # Update version delivery status based on overall result
        if succeeded == len(destinations):
            self._update_delivery_status(version_id, "delivered")
        elif succeeded > 0:
            self._update_delivery_status(version_id, "partial")
        else:
            self._update_delivery_status(version_id, "failed")

        logger.info(
            f"[DELIVERY] Multi-destination: {succeeded}/{len(destinations)} succeeded"
        )

        return MultiDestinationResult(
            total_destinations=len(destinations),
            succeeded=succeeded,
            failed=failed,
            results=results,
            all_succeeded=(succeeded == len(destinations)),
        )

    def _log_destination_delivery(
        self,
        version_id: str,
        agent_id: str,
        user_id: str,
        destination_index: int,
        destination: dict[str, Any],
        result: ExportResult,
    ) -> None:
        """Log a multi-destination delivery to the destination_delivery_log table."""
        try:
            self.client.table("destination_delivery_log").insert({
                "run_id": version_id,
                "agent_id": agent_id,
                "user_id": user_id,
                "destination_index": destination_index,
                "destination": destination,
                "platform": destination.get("platform", "unknown"),
                "status": "delivered" if result.status == ExportStatus.SUCCESS else "failed",
                "external_id": result.external_id,
                "external_url": result.external_url,
                "error_message": result.error_message,
                "completed_at": datetime.now(timezone.utc).isoformat() if result.status == ExportStatus.SUCCESS else None,
            }).execute()
        except Exception as e:
            logger.warning(f"[DELIVERY] Failed to log destination delivery: {e}")


def get_delivery_service(client) -> DeliveryService:
    """
    Get a DeliveryService instance.

    Args:
        client: Supabase client

    Returns:
        DeliveryService instance
    """
    return DeliveryService(client)


# =============================================================================
# ADR-118 D.3: Workspace-based delivery (reads from output folder, not agent_runs)
# =============================================================================


async def deliver_from_output_folder(
    client,
    user_id: str,
    agent: dict,
    output_folder: str,
    agent_slug: str,
    version_id: str,
    version_number: int,
    destination: dict | None = None,
    task_slug: str | None = None,
) -> ExportResult:
    """
    Deliver agent output by reading from workspace output folder instead of agent_runs.

    ADR-118 D.3: Output folders are the single delivery source. This function:
    1. Reads output.md + manifest.json from the output folder
    2. Dispatches to the appropriate exporter (email via Resend, others via existing exporters)
    3. Updates the manifest with delivery status

    For email destinations, rendered binary attachments from the manifest are included
    as download links in the email body, sourced from the manifest.

    Args:
        client: Supabase service client
        user_id: User UUID
        agent: Full agent dict (needs title, role)
        output_folder: Relative output folder path (e.g., "outputs/2026-03-18T0900")
        agent_slug: Agent slug for workspace scoping
        version_id: agent_run UUID (for audit trail updates)
        version_number: Run version number

    Returns:
        ExportResult with delivery status
    """
    import json

    from services.workspace import AgentWorkspace

    ws = AgentWorkspace(client, user_id, agent_slug)

    # 1. Read text content from output folder
    text_content = await ws.read(f"{output_folder}/output.md")
    if not text_content:
        return ExportResult(
            status=ExportStatus.FAILED,
            error_message=f"Output content not found at {output_folder}/output.md",
        )

    # 1b. ADR-130 Phase 2: Check for composed HTML (post-generation compose step)
    composed_html = await ws.read(f"{output_folder}/output.html")

    # 2. Read manifest
    manifest_raw = await ws.read(f"{output_folder}/manifest.json")
    manifest = {}
    if manifest_raw:
        try:
            manifest = json.loads(manifest_raw)
        except json.JSONDecodeError:
            logger.warning(f"[DELIVERY] Invalid manifest JSON at {output_folder}")

    # 3. Get destination (prefer explicit param, fall back to agent record)
    if not destination:
        destination = None  # Column dropped — destination no longer on agents table
    if not destination:
        return ExportResult(
            status=ExportStatus.FAILED,
            error_message="No destination configured",
        )

    platform = destination.get("platform")
    if not platform:
        return ExportResult(
            status=ExportStatus.FAILED,
            error_message="No platform specified in destination",
        )

    title = agent.get("title", "YARNNN Agent")
    role = agent.get("role")

    # 4. For email: build HTML with rendered attachments from manifest, then send via Resend
    if platform == "email":
        user_timezone = get_user_timezone(client, user_id)
        result = await _deliver_email_from_manifest(
            destination=destination,
            text_content=text_content,
            manifest=manifest,
            title=title,
            version_number=version_number,
            role=role,
            agent_id=str(agent.get("id", "")),
            mode=None,  # Mode is on tasks, not agents (ADR-138)
            composed_html=composed_html,
            task_slug=task_slug,
            user_timezone=user_timezone,
        )
    else:
        # Non-email platforms: fall back to existing exporter registry
        # (reads text_content directly, not from agent_runs)
        registry = get_exporter_registry()
        exporter = registry.get(platform)
        if not exporter:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=f"No exporter for platform: {platform}",
            )

        token_manager = get_token_manager()
        context = await _get_exporter_context_standalone(client, user_id, platform, token_manager)
        if exporter.requires_auth and not context:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=f"No {platform} integration connected",
            )

        result = await exporter.deliver(
            destination=destination,
            content=text_content,
            title=title,
            metadata={
                "agent_id": str(agent.get("id", "")),
                "version_id": version_id,
                "version_number": version_number,
                "role": role,
                "mode": None,  # Mode is on tasks, not agents (ADR-138)
            },
            context=context,
        )

    # 5. Update manifest with delivery status
    if result.status == ExportStatus.SUCCESS:
        try:
            delivery_status = {
                "channel": platform,
                "status": "delivered",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "external_id": result.external_id,
                "external_url": result.external_url,
            }
            await ws.update_manifest_delivery(output_folder, delivery_status)
        except Exception as e:
            logger.warning(f"[DELIVERY] Manifest delivery update failed (non-fatal): {e}")

    return result


# deliver_from_assembly_folder — REMOVED (project assembly dissolved)


def _build_email_assets_from_manifest(manifest: dict) -> list[dict]:
    """Build compose asset refs from manifest-rendered files.

    Email composition happens from markdown, so any local image/chart references
    need manifest `content_url` resolution just like web composition.
    """
    assets: list[dict] = []
    seen: set[str] = set()

    for file_info in manifest.get("files", []) or []:
        content_url = (file_info or {}).get("content_url")
        path = ((file_info or {}).get("path") or "").strip()
        if not content_url or not path or path == "output.md":
            continue

        refs = {path}
        if "/" in path:
            refs.add(path.rsplit("/", 1)[-1])

        for ref in refs:
            if ref and ref not in seen:
                assets.append({"ref": ref, "url": content_url})
                seen.add(ref)

    return assets


def _inject_into_body(html_doc: str, snippet: str) -> str:
    """Insert a snippet before </body>, or append if no body tag is present."""
    if not snippet:
        return html_doc

    match = re.search(r"</body\s*>", html_doc, flags=re.IGNORECASE)
    if not match:
        return f"{html_doc}{snippet}"
    return f"{html_doc[:match.start()]}{snippet}{html_doc[match.start():]}"


def _fallback_email_html(
    *,
    title: str,
    text_content: str,
    composed_html: Optional[str] = None,
) -> str:
    """Build the safest available HTML fallback for email delivery.

    Order of preference:
    1. Reuse already-composed HTML from the output folder, sanitized for email.
    2. Minimal escaped markdown fallback.
    """
    if composed_html:
        sanitized = re.sub(
            r"<script\b[^>]*>.*?</script>",
            "",
            composed_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        sanitized = re.sub(
            r"<iframe\b[^>]*src=['\"]([^'\"]+)['\"][^>]*>.*?</iframe>",
            r'<p><a href="\1">Open embedded content</a></p>',
            sanitized,
            flags=re.IGNORECASE | re.DOTALL,
        )
        sanitized = re.sub(
            r"<iframe\b[^>]*>\s*</iframe>",
            "",
            sanitized,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if sanitized.strip():
            return sanitized

    return (
        "<html><body><div style='font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
        "max-width:600px;margin:0 auto;padding:24px;color:#1a1a1a;line-height:1.6'>"
        f"<h1 style='margin:0 0 16px;font-size:22px'>{html.escape(title)}</h1>"
        f"<pre style='white-space:pre-wrap;font-size:14px'>{html.escape(text_content)}</pre>"
        "</div></body></html>"
    )


async def _deliver_email_from_manifest(
    destination: dict,
    text_content: str,
    manifest: dict,
    title: str,
    version_number: int,
    role: Optional[str],
    agent_id: str,
    mode: Optional[str],
    composed_html: Optional[str] = None,
    task_slug: Optional[str] = None,
    user_timezone: str = "UTC",
) -> ExportResult:
    """ADR-118 D.3 + ADR-148: Email delivery sourced from output folder.

    Always composes email-optimized HTML via compose engine (surface_type="digest").
    The pre-composed HTML (output.html) is for web display — email needs its own
    rendering with inline-safe CSS, no CSS variables, no external scripts.
    Includes rendered binary download links from the manifest.
    """
    import os
    from jobs.email import send_email

    target = destination.get("target")
    if not target:
        return ExportResult(
            status=ExportStatus.FAILED,
            error_message="No recipient email specified",
        )

    options = destination.get("options", {})

    # Subject clock should reflect when this run happened in the user's timezone.
    subject_time = datetime.now(timezone.utc)
    raw_created_at = (manifest or {}).get("created_at")
    if isinstance(raw_created_at, str) and raw_created_at.strip():
        try:
            parsed = datetime.fromisoformat(raw_created_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            subject_time = parsed.astimezone(timezone.utc)
        except Exception:
            pass

    timestamp_str = format_datetime_for_timezone(
        subject_time,
        user_timezone=user_timezone,
        fmt="%b %-d %H:%M %Z",
    )
    if version_number:
        default_subject = f"{title} v{version_number} — {timestamp_str}"
    else:
        default_subject = f"{title} — {timestamp_str}"
    subject = options.get("subject", default_subject)

    # ADR-148: Compose email-specific HTML via render service (surface_type="digest")
    html_body = await _compose_email_html(
        text_content,
        title,
        assets=_build_email_assets_from_manifest(manifest),
    )
    if not html_body:
        logger.warning("[DELIVERY] Email compose failed — using HTML fallback")
        html_body = _fallback_email_html(
            title=title,
            text_content=text_content,
            composed_html=composed_html,
        )

    # Append email footer (feedback link + yarnnn branding)
    app_url = os.environ.get("APP_URL", "https://yarnnn.com")
    if task_slug:
        view_url = f"{app_url}/tasks/{task_slug}"
    elif agent_id:
        view_url = f"{app_url}/agents/{agent_id}"
    else:
        view_url = app_url

    footer_html = (
        '<div style="margin-top:32px;padding-top:20px;border-top:1px solid #e5e7eb;text-align:center;">'
        f'<a href="{view_url}" style="display:inline-block;background:#111;color:#fff;'
        f'padding:10px 24px;text-decoration:none;border-radius:9999px;font-weight:500;font-size:14px;">'
        f'Reply with feedback</a>'
        '<p style="color:#9ca3af;font-size:12px;margin-top:12px;">'
        'Tell the agent what to change — it learns from your feedback.</p>'
        f'<p style="color:#9ca3af;font-size:11px;margin-top:12px;">'
        f'Delivered by <a href="{app_url}" style="color:#9ca3af;">yarnnn</a> · '
        f'<a href="{app_url}/settings" style="color:#9ca3af;">Manage notifications</a></p>'
        '</div>'
    )
    html_body = _inject_into_body(html_body, footer_html)

    # ADR-118 D.3: Include rendered binary attachments from manifest
    files = manifest.get("files", [])
    rendered_files = [f for f in files if f.get("content_url")]
    if rendered_files:
        links = []
        for f in rendered_files:
            fname = f.get("path", "file")
            url = f["content_url"]
            size = f.get("size_bytes", 0)
            size_str = f" ({size // 1024}KB)" if size > 0 else ""
            links.append(
                f'<li><a href="{url}" style="color:#1a56db;text-decoration:underline;">'
                f'{fname}</a>{size_str}</li>'
            )
        attachment_html = (
            '<div style="margin-top:24px;padding:16px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">'
            '<p style="margin:0 0 8px 0;font-weight:600;font-size:14px;">Attachments</p>'
            f'<ul style="margin:0;padding-left:20px;">{"".join(links)}</ul>'
            '</div>'
        )
        html_body = _inject_into_body(html_body, attachment_html)

    try:
        result = await send_email(
            to=target,
            subject=subject,
            html=html_body,
            text=text_content,
        )
        if result.success:
            logger.info(f"[DELIVERY] Email delivered to {target}, message_id={result.message_id}")
            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=result.message_id,
                metadata={"format": "html", "recipient": target, "channel": "resend"},
            )
        else:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=result.error or "Resend delivery failed",
            )
    except Exception as e:
        logger.error(f"[DELIVERY] Email delivery failed: {e}")
        return ExportResult(
            status=ExportStatus.FAILED,
            error_message=str(e),
        )


async def _compose_email_html(
    markdown: str,
    title: str,
    assets: Optional[list[dict]] = None,
) -> Optional[str]:
    """Call render service compose endpoint with surface_type=digest for email delivery.

    ADR-170: Email delivery uses the digest surface type — scannable, mobile-first,
    email-safe CSS (no CSS variables, no JS, inline-friendly).
    """
    import httpx
    import os

    render_url = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")
    render_secret = os.environ.get("RENDER_SERVICE_SECRET", "")

    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            headers = {}
            if render_secret:
                headers["X-Render-Secret"] = render_secret

            resp = await http.post(
                f"{render_url}/compose",
                json={
                    "markdown": markdown,
                    "title": title,
                    "surface_type": "digest",
                    "assets": assets or [],
                },
                headers=headers,
            )

            if resp.status_code != 200:
                logger.warning(f"[DELIVERY] Email compose HTTP {resp.status_code}")
                return None

            data = resp.json()
            if data.get("success") and data.get("html"):
                logger.info(f"[DELIVERY] Email composed via render service ({len(data['html'])} chars)")
                return data["html"]
            return None

    except Exception as e:
        logger.warning(f"[DELIVERY] Email compose call failed: {e}")
        return None


async def _get_exporter_context_standalone(
    client, user_id: str, platform: str, token_manager
) -> Optional[ExporterContext]:
    """Get auth context for an exporter (standalone version for workspace-based delivery)."""
    if platform in ("download", "email"):
        return ExporterContext(user_id=user_id, access_token="", metadata={})

    lookup_candidates = [platform]

    try:
        for candidate in lookup_candidates:
            try:
                result = client.table("platform_connections").select(
                    "credentials_encrypted, refresh_token_encrypted, metadata, status"
                ).eq("user_id", user_id).eq("platform", candidate).single().execute()
                if result.data and result.data["status"] == "active":
                    access_token = token_manager.decrypt(result.data["credentials_encrypted"])
                    refresh_token = None
                    if result.data.get("refresh_token_encrypted"):
                        refresh_token = token_manager.decrypt(result.data["refresh_token_encrypted"])
                    return ExporterContext(
                        user_id=user_id,
                        access_token=access_token,
                        refresh_token=refresh_token,
                        metadata=result.data.get("metadata", {}) or {},
                    )
            except Exception:
                continue
        return None
    except Exception as e:
        logger.error(f"[DELIVERY] Failed to get context for {platform}: {e}")
        return None
