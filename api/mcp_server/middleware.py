"""
MCP Server Transport Authentication — ADR-075

Layer 1 (transport auth): Validates bearer token on HTTP requests.
Gates access to the MCP endpoint. Static token for internal/operator use.

Layer 2 (3rd-party/OAuth): Future — will validate JWT signature + audience
for ChatGPT developer mode and other external MCP clients.
"""

import hmac
import os
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Validate bearer token on MCP transport requests."""

    async def dispatch(self, request: Request, call_next):
        # Health check bypasses auth
        if request.url.path == "/health":
            return await call_next(request)

        expected_token = os.environ.get("MCP_BEARER_TOKEN")
        if not expected_token:
            logger.error("[MCP Auth] MCP_BEARER_TOKEN not configured — rejecting request")
            return JSONResponse(
                {"error": "Server auth not configured"}, status_code=503
            )

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing Authorization: Bearer <token>"}, status_code=401
            )

        token = auth_header[7:]  # Strip "Bearer "
        if not hmac.compare_digest(token, expected_token):
            return JSONResponse({"error": "Invalid token"}, status_code=401)

        return await call_next(request)
