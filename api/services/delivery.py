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

    # 1b. ADR-213: compose HTML on demand via the shared helper. The render
    # service caches by content hash, so repeat deliveries on unchanged
    # substrate are ~10ms. Requires task_slug to resolve the task workspace
    # (where section partials + sys_manifest.json live); without it, email
    # delivery falls back to markdown-only body.
    composed_html: Optional[str] = None
    if task_slug:
        try:
            from services.compose.task_html import compose_task_output_html
            _date_folder = output_folder.removeprefix("outputs/").split("/", 1)[0]
            composed_html = await compose_task_output_html(
                client, user_id, task_slug, _date_folder
            )
        except Exception as _e:  # noqa: BLE001
            logger.warning(f"[DELIVERY] On-demand compose failed for {task_slug}/{output_folder}: {_e}")

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

    # ADR-202 §3: delivery_requires_approval gate.
    # Compose writes the output + manifest to /tasks/{slug}/outputs/{date}/
    # regardless. Distribution fires only after operator clicks Ship Now
    # in the cockpit Work surface (Phase 3 frontend UX). Until that
    # timestamp is set, this function returns a skipped-for-approval
    # status and writes `pending_distribution: true` to the manifest so
    # the cockpit can surface the pending badge.
    if task_slug:
        # ADR-231 Phase 3.6.b: type_key + TASK.md registry lookup retired.
        # Recurrence declarations carry an explicit `requires_approval:` field
        # under `delivery:` when the operator wants the gate. Default = False.
        requires_approval = False
        try:
            from services.recurrence import walk_workspace_recurrences
            _decls = walk_workspace_recurrences(client, user_id)
            _decl = next((d for d in _decls if d.slug == task_slug), None)
            if _decl is not None:
                _delivery_block = _decl.data.get("delivery")
                if isinstance(_delivery_block, dict):
                    requires_approval = bool(_delivery_block.get("requires_approval", False))
        except Exception as _exc:  # noqa: BLE001
            logger.warning(
                f"[DELIVERY] requires_approval lookup failed for task={task_slug}: {_exc}"
            )

        if requires_approval:
            approved_at = manifest.get("pending_distribution_approved_at")
            if not approved_at:
                # Write / update the manifest flag and return a skipped status.
                # The cockpit polls this via task-detail; Phase 3 frontend
                # surfaces the Ship Now affordance which flips the flag.
                import json
                manifest["pending_distribution"] = True
                try:
                    await ws.write(
                        f"{output_folder}/manifest.json",
                        json.dumps(manifest, indent=2),
                        summary="ADR-202 §3: pending operator approval for distribution",
                    )
                except Exception as _exc:  # noqa: BLE001
                    logger.warning(
                        f"[DELIVERY] Failed to persist pending_distribution flag for {task_slug}: {_exc}"
                    )
                logger.info(
                    f"[DELIVERY] task={task_slug} awaits operator approval (ADR-202 §3) — skipping ship"
                )
                return ExportResult(
                    status=ExportStatus.SKIPPED,
                    error_message="pending_distribution_approval",
                )
            # Approved — fall through to normal delivery path.
            logger.info(
                f"[DELIVERY] task={task_slug} operator-approved at {approved_at} — proceeding"
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
            user_id=user_id,
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
    user_id: Optional[str] = None,
) -> ExportResult:
    """ADR-118 D.3 + ADR-148 + ADR-213: Email delivery sourced from output folder.

    Composes email-optimized HTML via compose engine (surface_type="digest")
    with inline-safe CSS, no CSS variables, no external scripts. Web display
    composition happens separately via compose_task_output_html() (ADR-213 —
    no pre-rendered output.html exists in the workspace).
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

    # ADR-183 Phase 2: "subscribers" target → resolve emails from commerce API
    if target == "subscribers":
        return await _deliver_to_subscribers(
            destination=destination,
            text_content=text_content,
            manifest=manifest,
            title=title,
            version_number=version_number,
            role=role,
            agent_id=agent_id,
            mode=mode,
            composed_html=composed_html,
            task_slug=task_slug,
            user_timezone=user_timezone,
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

    # ADR-202 §1: daily-update email is an expository pointer, not a
    # full-content digest. The agent-generated content lives at
    # /tasks/daily-update/outputs/{date}/ and the Overview surface
    # (ADR-199) renders it. The email is just the invitation.
    # Compute deterministic headline counts + swap the body for the
    # pointer template. Empty workspace is already handled by
    # _execute_daily_update_empty_state earlier in the pipeline.
    html_body: Optional[str] = None
    if task_slug == "daily-update" and user_id:
        try:
            from services.daily_update_email import (
                build_pointer_html,
                build_pointer_markdown,
                compute_daily_headline_counts,
            )
            from services.supabase import get_service_client
            from services.schedule_utils import format_daily_local_time_label

            # Scheduler-invoked path — use service client for read-only counts.
            sc = get_service_client()
            counts = await compute_daily_headline_counts(sc, user_id)
            schedule_label = format_daily_local_time_label(user_timezone)
            html_body = build_pointer_html(counts, schedule_label=schedule_label)
            # Replace plain-text body with markdown pointer form.
            text_content = build_pointer_markdown(counts, schedule_label=schedule_label)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[DELIVERY] daily-update pointer template failed — falling back to compose: %s",
                exc,
            )
            html_body = None  # falls into the normal compose path below

    if html_body is None:
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
    # ADR-201: agent routes moved from /agents/ → /team?agent=. Task routes
    # remain /tasks/ for backend-canonical deep-links (frontend may redirect).
    if task_slug:
        view_url = f"{app_url}/tasks/{task_slug}"
    elif agent_id:
        view_url = f"{app_url}/team?agent={agent_id}"
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


# =============================================================================
# ADR-183 Phase 2: Subscriber Delivery
# =============================================================================

async def _deliver_to_subscribers(
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
    """Deliver to all active subscribers via commerce provider.

    ADR-183: Live-reads subscriber list from commerce API at delivery time.
    No cached subscriber list — commerce provider is the source of truth.
    Sends individually via the existing email path.
    """
    # Resolve product_id from destination metadata (set from TASK.md **Commerce:** field)
    product_id = destination.get("product_id")

    try:
        from integrations.core.lemonsqueezy_client import get_commerce_client
        from integrations.core.tokens import get_token_manager

        # Get commerce credentials
        from services.supabase import get_service_client
        service_client = get_service_client()

        # Find user_id from agent_id
        user_id = None
        if agent_id:
            agent_result = service_client.table("agents").select(
                "user_id"
            ).eq("id", agent_id).single().execute()
            if agent_result.data:
                user_id = agent_result.data["user_id"]

        if not user_id:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="Cannot resolve user for subscriber delivery",
            )

        conn_result = service_client.table("platform_connections").select(
            "credentials_encrypted"
        ).eq("user_id", user_id).eq("platform", "commerce").eq(
            "status", "active"
        ).single().execute()

        if not conn_result.data:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="No active commerce connection for subscriber delivery",
            )

        token_manager = get_token_manager()
        api_key = token_manager.decrypt(conn_result.data["credentials_encrypted"])

        commerce_client = get_commerce_client()
        subscribers = await commerce_client.get_subscribers(
            api_key=api_key, product_id=product_id,
        )

        if not subscribers:
            logger.info(f"[DELIVERY] No active subscribers to deliver to")
            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id="no_subscribers",
            )

        # Deliver to each subscriber individually
        sent = 0
        failed = 0
        for sub in subscribers:
            if not sub.email:
                continue
            try:
                sub_destination = {
                    "platform": "email",
                    "target": sub.email,
                    "format": "send",
                }
                result = await _deliver_email_from_manifest(
                    destination=sub_destination,
                    text_content=text_content,
                    manifest=manifest,
                    title=title,
                    version_number=version_number,
                    role=role,
                    agent_id=agent_id,
                    mode=mode,
                    composed_html=composed_html,
                    task_slug=task_slug,
                    user_timezone=user_timezone,
                )
                if result.status == ExportStatus.SUCCESS:
                    sent += 1
                else:
                    failed += 1
                    logger.warning(f"[DELIVERY] Subscriber delivery failed for {sub.email}: {result.error_message}")
            except Exception as e:
                failed += 1
                logger.error(f"[DELIVERY] Subscriber delivery error for {sub.email}: {e}")

        logger.info(f"[DELIVERY] Subscriber delivery: {sent} sent, {failed} failed out of {len(subscribers)}")

        if sent > 0:
            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=f"subscribers:{sent}/{len(subscribers)}",
            )
        return ExportResult(
            status=ExportStatus.FAILED,
            error_message=f"All {failed} subscriber deliveries failed",
        )

    except Exception as e:
        logger.error(f"[DELIVERY] Subscriber delivery error: {e}")
        return ExportResult(
            status=ExportStatus.FAILED,
            error_message=f"Subscriber delivery failed: {str(e)}",
        )
