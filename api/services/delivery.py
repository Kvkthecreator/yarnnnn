"""
Delivery Service - ADR-028, ADR-031 Phase 6, ADR-040

Governance-aware delivery orchestration for destination-first deliverables.

This service handles:
1. Determining when delivery should occur based on governance level
2. Orchestrating the actual delivery via exporters
3. Tracking delivery status on versions
4. Retry logic for failed deliveries
5. Multi-destination delivery for synthesizers (ADR-031 Phase 6)
6. Sending notifications on delivery events (ADR-040)

Governance Levels:
- manual: User must explicitly trigger delivery (click Export button)
- semi_auto: Delivery triggers automatically when version is approved
- full_auto: Delivery happens immediately after generation (skip staging)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any

from integrations.core.types import ExportResult, ExportStatus
from integrations.core.tokens import get_token_manager
from integrations.exporters import get_exporter_registry, ExporterContext

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
        if service.should_auto_deliver(deliverable):
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

    def should_auto_deliver(self, deliverable: dict[str, Any]) -> bool:
        """
        Determine if a deliverable should auto-deliver on approval.

        Args:
            deliverable: The deliverable record

        Returns:
            True if auto-delivery should occur
        """
        governance = deliverable.get("governance", "manual")
        destination = deliverable.get("destination")

        # Must have destination configured
        if not destination:
            return False

        # Only semi_auto and full_auto trigger automatic delivery
        return governance in ("semi_auto", "full_auto")

    def get_style_context(self, deliverable: dict[str, Any]) -> Optional[str]:
        """
        Infer style context from destination platform.

        ADR-028: If destination is set, use platform as style context.
        This lets content generation adapt to the destination format.

        Args:
            deliverable: The deliverable record

        Returns:
            Style context string, or None if no destination
        """
        destination = deliverable.get("destination")
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
            version_id: The deliverable version ID
            user_id: The user ID (for auth)
            retry_count: Number of retries attempted

        Returns:
            ExportResult with delivery status
        """
        try:
            # 1. Get version and deliverable
            version = self.client.table("deliverable_versions").select(
                "id, deliverable_id, final_content, status, delivery_status"
            ).eq("id", version_id).single().execute()

            if not version.data:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message="Version not found"
                )

            # 2. Get deliverable with destination
            deliverable = self.client.table("deliverables").select(
                "id, title, destination, governance, user_id"
            ).eq("id", version.data["deliverable_id"]).single().execute()

            if not deliverable.data:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message="Deliverable not found"
                )

            # 3. Verify destination is configured
            destination = deliverable.data.get("destination")
            if not destination:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message="No destination configured"
                )

            platform = destination.get("platform")
            if not platform:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message="No platform specified in destination"
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
            title = deliverable.data.get("title", "YARNNN Deliverable")

            result = await exporter.deliver(
                destination=destination,
                content=content,
                title=title,
                metadata={
                    "deliverable_id": deliverable.data["id"],
                    "version_id": version_id,
                    "retry_count": retry_count
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
                # ADR-040: Send notification for semi_auto governance
                governance = deliverable.data.get("governance", "manual")
                if governance == "semi_auto":
                    await self._notify_delivered(
                        user_id=user_id,
                        deliverable_id=deliverable.data["id"],
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
                    deliverable_id=deliverable.data["id"],
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
        # Download doesn't need auth
        if platform == "download":
            return ExporterContext(
                user_id=user_id,
                access_token="",
                metadata={}
            )

        try:
            # Get user's integration
            integration = self.client.table("user_integrations").select(
                "access_token_encrypted, refresh_token_encrypted, metadata, status"
            ).eq("user_id", user_id).eq("provider", platform).single().execute()

            if not integration.data:
                return None

            if integration.data["status"] != "active":
                return None

            # Decrypt token
            access_token = self.token_manager.decrypt(
                integration.data["access_token_encrypted"]
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
            update["delivered_at"] = datetime.utcnow().isoformat()

        self.client.table("deliverable_versions").update(update).eq(
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
                "deliverable_version_id": version_id,
                "user_id": user_id,
                "provider": platform,
                "destination": destination,
                "status": result.status.value,
                "external_id": result.external_id,
                "external_url": result.external_url,
                "error_message": result.error_message,
                "completed_at": datetime.utcnow().isoformat() if result.status == ExportStatus.SUCCESS else None
            }).execute()
        except Exception as e:
            logger.warning(f"[DELIVERY] Failed to log export: {e}")

    # =========================================================================
    # ADR-040: Notification Helpers
    # =========================================================================

    async def _notify_delivered(
        self,
        user_id: str,
        deliverable_id: str,
        title: str,
        platform: str,
        target: Optional[str],
        external_url: Optional[str],
    ) -> None:
        """Send notification when deliverable is delivered (semi_auto governance)."""
        try:
            from services.notifications import notify_deliverable_delivered
            destination_str = f"{platform}"
            if target:
                destination_str += f" ({target})"
            await notify_deliverable_delivered(
                db_client=self.client,
                user_id=user_id,
                deliverable_id=deliverable_id,
                deliverable_title=title,
                destination=destination_str,
                external_url=external_url,
            )
        except Exception as e:
            logger.warning(f"[DELIVERY] Failed to send delivery notification: {e}")

    async def _notify_failed(
        self,
        user_id: str,
        deliverable_id: str,
        title: str,
        error: str,
    ) -> None:
        """Send notification when delivery fails."""
        try:
            from services.notifications import notify_deliverable_failed
            await notify_deliverable_failed(
                db_client=self.client,
                user_id=user_id,
                deliverable_id=deliverable_id,
                deliverable_title=title,
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
            version_id: The deliverable version ID
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
        version = self.client.table("deliverable_versions").select(
            "id, deliverable_id, final_content, draft_content"
        ).eq("id", version_id).single().execute()

        if not version.data:
            return MultiDestinationResult(
                total_destinations=len(destinations),
                succeeded=0,
                failed=len(destinations),
                results=[{"error": "Version not found"}],
                all_succeeded=False,
            )

        # Get deliverable title
        deliverable = self.client.table("deliverables").select(
            "id, title, platform_variant"
        ).eq("id", version.data["deliverable_id"]).single().execute()

        content = version.data.get("final_content") or version.data.get("draft_content", "")
        title = deliverable.data.get("title", "YARNNN Deliverable") if deliverable.data else "Deliverable"
        platform_variant = deliverable.data.get("platform_variant") if deliverable.data else None

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
                        "deliverable_id": version.data["deliverable_id"],
                        "version_id": version_id,
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
                        deliverable_id=version.data["deliverable_id"],
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
        deliverable_id: str,
        user_id: str,
        destination_index: int,
        destination: dict[str, Any],
        result: ExportResult,
    ) -> None:
        """Log a multi-destination delivery to the destination_delivery_log table."""
        try:
            self.client.table("destination_delivery_log").insert({
                "version_id": version_id,
                "deliverable_id": deliverable_id,
                "user_id": user_id,
                "destination_index": destination_index,
                "destination": destination,
                "platform": destination.get("platform", "unknown"),
                "status": "delivered" if result.status == ExportStatus.SUCCESS else "failed",
                "external_id": result.external_id,
                "external_url": result.external_url,
                "error_message": result.error_message,
                "completed_at": datetime.utcnow().isoformat() if result.status == ExportStatus.SUCCESS else None,
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
