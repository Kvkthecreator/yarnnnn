"""
YARNNN MCP Server entry point — ADR-075

Run from the api/ directory (same pattern as unified_scheduler):
    cd api && python -m mcp_server          # stdio (Claude Desktop/Code)
    cd api && python -m mcp_server http     # Streamable HTTP (ChatGPT, remote)
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load .env before any service imports (matches main.py pattern)
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from mcp_server.server import mcp

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport == "http":
        import uvicorn

        port = int(os.environ.get("PORT", "8000"))
        app = mcp.streamable_http_app()

        # Security (2026-08-03): throttle the OAuth auth paths (/token,
        # /register, /authorize) against online guessing + registration spam.
        from mcp_server.rate_limit import AuthRateLimitMiddleware
        app = AuthRateLimitMiddleware(app)

        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
