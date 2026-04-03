"""
fetch-asset skill — ADR-157

Fetch external visual assets (favicons, logos) from URLs.
Returns raw bytes for upload to Supabase Storage by the gateway.

Favicon-first: uses Google Favicon API (deterministic, free, fast).
"""

import httpx

# Google Favicon API — deterministic, no API key needed
FAVICON_API = "https://www.google.com/s2/favicons"

# Constraints
MAX_ASSET_BYTES = 1 * 1024 * 1024  # 1MB
FETCH_TIMEOUT = 10.0  # seconds
VALID_FAVICON_SIZES = {16, 32, 64, 128, 256}


def _normalize_domain(url: str) -> str:
    """Extract clean domain from URL or domain string."""
    url = url.strip()
    # Remove protocol
    for prefix in ("https://", "http://", "//"):
        if url.startswith(prefix):
            url = url[len(prefix):]
    # Remove path, query, fragment
    url = url.split("/")[0].split("?")[0].split("#")[0]
    # Remove www. prefix
    if url.startswith("www."):
        url = url[4:]
    return url.lower()


def _clamp_size(size: int) -> int:
    """Clamp favicon size to nearest valid value."""
    if size <= 16:
        return 16
    if size >= 256:
        return 256
    # Find nearest valid size
    return min(VALID_FAVICON_SIZES, key=lambda s: abs(s - size))


async def render_fetch_asset(input_data: dict, output_format: str) -> tuple[bytes, str]:
    """Fetch an external visual asset and return raw bytes.

    Args:
        input_data: {url, asset_type, size}
        output_format: Desired format (png, ico, etc.)

    Returns:
        (file_bytes, content_type)
    """
    url = input_data.get("url", "")
    asset_type = input_data.get("asset_type", "favicon")
    size = input_data.get("size", 64)

    if not url:
        raise ValueError("url is required")

    if asset_type == "favicon":
        return await _fetch_favicon(url, size)
    else:
        raise ValueError(f"Unsupported asset_type: {asset_type}. Currently supported: favicon")


async def _fetch_favicon(url: str, size: int) -> tuple[bytes, str]:
    """Fetch favicon via Google Favicon API."""
    domain = _normalize_domain(url)
    if not domain:
        raise ValueError("Could not extract domain from url")

    size = _clamp_size(size)

    favicon_url = f"{FAVICON_API}?domain={domain}&sz={size}"

    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(favicon_url)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "image/png")
        file_bytes = resp.content

        if len(file_bytes) > MAX_ASSET_BYTES:
            raise ValueError(f"Asset too large: {len(file_bytes)} bytes (max {MAX_ASSET_BYTES})")

        if not file_bytes:
            raise ValueError(f"Empty response from favicon API for domain: {domain}")

        # Normalize content type
        if "png" in content_type:
            content_type = "image/png"
        elif "ico" in content_type or "icon" in content_type:
            content_type = "image/x-icon"
        elif "svg" in content_type:
            content_type = "image/svg+xml"
        else:
            content_type = "image/png"  # Default

        return file_bytes, content_type
