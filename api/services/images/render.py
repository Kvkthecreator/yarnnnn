"""Render-to-raster — the composition is the SOURCE, the PNG is a DERIVATION.

This is the moat claim no design tool can make. Canva can export a PNG; it
cannot tell you which revision of which composition produced it, who authored
that revision, or what the object it came from was made from. Here the export
is an **attributed derivation on the ledger**:

    revision_kind = "derivation"        (ADR-423 — this is a derived act)
    derived_from  = [the stage's path]  (ADR-448 — the reference edge)

so `trace` walks an exported ad back to the composition and the revision that
produced it, and `list_dependents` answers "what was made from this stage?".
ADR-427 Phase 2 is what made this possible: the PNG is a real binary revision
in the CAS, not a file dropped in a bucket.

── WHY SERVER-SIDE (ADR-472 D5) ─────────────────────────────────────────────
Client-side DOM→PNG would ship faster and keep ADR-417 untouched, but the
bytes would be produced on an unattested client and "this PNG is a derivation
of that composition at that revision" becomes a CLAIM rather than a FACT.
Provenance is the moat, so the raster is produced where it can be attested.

ADR-417's principle survives by RENTING the engine: `RenderBackend` is the
driver seam, and yarnnn hosts no rendering service. The first driver is a
headless browser invoked as a local process — which is a rented capability in
the sense that matters (nothing is hosted, nothing is operated, the binary is
the platform's), and a hosted-API driver is a config swap from here.

── CITATIONS MUST BE RESOLVED BEFORE RASTERIZING ────────────────────────────
The composition cites its leaves by workspace path (`data-ref`), which no
browser can fetch: the paths are substrate keys, not URLs, and the renderer
holds no session. So the projection INLINES each cited leaf as a data URI
before handing the document to the driver. This is the same
source-vs-projection split ADR-456 drew for markdown: the substrate keeps
citations, the projection carries bytes, and the projection is never a second
source.

Canonical reference: docs/adr/ADR-474-decomposed-generation.md
"""

from __future__ import annotations

import base64
import logging
import re
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RenderBackend(ABC):
    """Rasterize a composed document at an exact size.

    The contract ADR-472 D5 named. `render` returns PNG bytes or raises;
    `available()` says whether the driver can run at all, so the endpoint can
    answer 503 honestly instead of failing mid-write.
    """

    name: str = "abstract"

    @abstractmethod
    def render(self, html: str, *, width: int, height: int) -> bytes:
        raise NotImplementedError

    def available(self) -> bool:
        return True


#: Where a headless Chrome/Chromium might live. Checked in order; the first
#: that exists wins. A driver that finds none reports unavailable rather than
#: raising at render time — the difference between "this deployment cannot
#: rasterize" (a 503 the member can act on) and "your export failed" (noise).
_CHROME_CANDIDATES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


class HeadlessChromeBackend(RenderBackend):
    """Rasterize with a headless Chrome/Chromium the platform already has.

    Nothing is hosted and nothing is operated — the engine is the platform's
    browser binary, invoked per render and gone. That keeps ADR-417's "rented,
    not owned" principle honest while leaving the seam free for a hosted API
    driver (Browserless, ScreenshotOne) as a pure config swap.
    """

    name = "headless-chrome"

    def __init__(self) -> None:
        self._binary: Optional[str] = None
        for candidate in _CHROME_CANDIDATES:
            found = shutil.which(candidate) or (
                candidate if Path(candidate).exists() else None
            )
            if found:
                self._binary = found
                break

    def available(self) -> bool:
        return self._binary is not None

    def render(self, html: str, *, width: int, height: int) -> bytes:
        if not self._binary:
            raise RuntimeError("no headless browser available on this host")

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "stage.html"
            out = Path(tmp) / "stage.png"
            src.write_text(html, encoding="utf-8")
            subprocess.run(
                [
                    self._binary,
                    "--headless",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--hide-scrollbars",
                    # The stage is a fixed box, so the shot is EXACTLY it —
                    # the whole point of dimensions-first (ADR-472 D3).
                    f"--window-size={int(width)},{int(height)}",
                    "--default-background-color=00000000",  # honour transparency
                    f"--screenshot={out}",
                    # Let webfonts + layout settle; a raster of a half-laid-out
                    # page is worse than a slow one.
                    "--virtual-time-budget=4000",
                    src.as_uri(),
                ],
                capture_output=True,
                timeout=90,
                check=False,
            )
            if not out.exists() or out.stat().st_size == 0:
                raise RuntimeError("renderer produced no output")
            return out.read_bytes()


_BACKEND: RenderBackend = HeadlessChromeBackend()


def get_render_backend() -> RenderBackend:
    return _BACKEND


def set_render_backend(backend: RenderBackend) -> None:
    """Swap the driver (the hosted-API wiring point; tests use it too)."""
    global _BACKEND
    _BACKEND = backend


# ---------------------------------------------------------------------------
# The projection — citations become bytes, for the renderer only.
# ---------------------------------------------------------------------------

_REF_RE = re.compile(r'<img([^>]*?)data-ref="([^"]+)"([^>]*?)>')


def inline_citations(db_client: Any, *, user_id: str, html: str) -> str:
    """Resolve every `data-ref` to a data URI, for rasterization ONLY.

    The substrate keeps citations; this projection carries bytes. Nothing
    produced here is ever written back — doing so would make the projection a
    second source, which ADR-456 already ruled out.

    A leaf that cannot be resolved is left as-is rather than dropped: the
    raster shows a gap exactly where the composition has one, which is honest,
    where a silently-removed object would misrepresent the document.
    """
    from services.storage_backend import get_storage_backend
    from services.workspace_context import substrate_scope_filter

    backend = get_storage_backend(db_client)

    def _resolve(match: re.Match) -> str:
        before, path, after = match.group(1), match.group(2), match.group(3)
        lookup = path if path.startswith("/") else f"/workspace/{path}"
        try:
            # The sha lives on the REVISION (`workspace_file_versions.blob_sha`),
            # not on the file row — a binary file's `content` is '' by contract
            # (ADR-427 Phase 2), so reading the file row alone yields nothing.
            # `head_version_id` is the pointer that makes this one hop.
            rows = (
                db_client.table("workspace_files")
                .select("content_type,head_version_id")
                .eq(*substrate_scope_filter(user_id))
                .eq("path", lookup)
                .limit(1)
                .execute()
            ).data or []
            if not rows:
                logger.warning("[IMAGES] cited leaf not found: %s", lookup)
                return match.group(0)
            row = rows[0]
            head = row.get("head_version_id")
            if not head:
                logger.warning("[IMAGES] cited leaf has no head revision: %s", lookup)
                return match.group(0)
            rev = (
                db_client.table("workspace_file_versions")
                .select("blob_sha")
                .eq("id", head)
                .limit(1)
                .execute()
            ).data or []
            if not rev:
                return match.group(0)
            data = backend.get_blob(rev[0]["blob_sha"])
            mime = row.get("content_type") or "image/png"
            uri = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
            return f'<img{before}src="{uri}" data-ref="{path}"{after}>'
        except Exception as exc:  # noqa: BLE001 — a gap beats a failed export
            logger.warning("[IMAGES] could not inline %s: %s", lookup, exc)
            return match.group(0)

    return _REF_RE.sub(_resolve, html)


def raster_path(stage_path: str) -> str:
    """Where a stage's rendered raster lands: beside it, same stem.

    `operation/launch-ad/image.html` → `operation/launch-ad/image.png`

    Beside the source, because the export IS the deliverable a member reaches
    for and hiding it under `exports/` would make the thing they came for the
    hardest to find. The `.png` extension is what makes the Finder open it in
    the right viewer (ADR-473's type→app association).
    """
    return re.sub(r"\.html$", ".png", stage_path)
