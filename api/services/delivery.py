"""
Delivery Service - ADR-028

Governance-aware delivery orchestration for destination-first deliverables.

This service handles:
1. Determining when delivery should occur based on governance level
2. Orchestrating the actual delivery via exporters
3. Tracking delivery status on versions
4. Retry logic for failed deliveries

Governance Levels:
- manual: User must explicitly trigger delivery (click Export button)
- semi_auto: Delivery triggers automatically when version is approved
- full_auto: Delivery happens immediately after generation (skip staging)
"""

import logging
from datetime import datetime
from typing import Optional, Any

from integrations.core.types import ExportResult, ExportStatus
from integrations.core.tokens import get_token_manager
from integrations.exporters import get_exporter_registry, ExporterContext

logger = logging.getLogger(__name__)


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

            # 8. Update delivery status
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
            else:
                self._update_delivery_status(
                    version_id,
                    "failed",
                    error=result.error_message
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


def get_delivery_service(client) -> DeliveryService:
    """
    Get a DeliveryService instance.

    Args:
        client: Supabase client

    Returns:
        DeliveryService instance
    """
    return DeliveryService(client)
