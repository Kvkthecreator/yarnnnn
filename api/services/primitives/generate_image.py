"""GenerateImage primitive — ADR-568 D3.

Chat asks for an image; the KERNEL decides who renders it
(`services/capabilities.py::serve_generation`). This module never names a
vendor — it is the `WebSearch`/`serve_search` relationship, second instance.

WHY THIS EXISTS. On ChatGPT/Claude/Gemini, image generation appears to live
inside the one chat. Mechanically it does not: OpenAI attaches an image tool
to a mainline chat model and "the tool handles GPT Image model selection".
The unified feel comes from ONE CONVERSATION REACHING A SECOND ENGINE, not
from one engine with two output types — and reaching a second engine is
exactly what a tool with a resolver behind it does.

⚠️ CONSEQUENTIAL, deliberately. This primitive spends money and lands a
revision, so it is NOT in `READ_ONLY_PRIMITIVES` and it DOES pass the ADR-307
gate. Adding it to the read-only set to satisfy ADR-467 D4.a's subset check
would be defeating a gate in order to pass it; the ceiling is restated
instead (ADR-568 D3) — every `LANE_SURFACE_EXTRA` name is read-only OR an
artifact verb.

WHERE THE IMAGE LANDS. `write_revision(content_bytes=…)` — the ONE binary
substrate lane (ADR-510) — under `uploads/generated/`. Downloads-adjacent
because the bytes ARRIVED from outside (ADR-552's arrival framing) rather
than being authored in place. It is an ordinary file afterwards: attributed,
versioned, citable, movable, deletable.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


GENERATE_IMAGE_TOOL = {
    "name": "GenerateImage",
    "description": """Generate an image from a text description and save it to the workspace.

Use this when the member asks you to create, draw, generate, or illustrate an
image. The image is saved as a real workspace file and shown to the member.

Do NOT use this to read or look at an image the member already has — you can
see attached images directly.

Args:
- prompt: What to depict. Be specific about subject, composition, and style;
  a vague prompt produces a generic image.
- filename: Short kebab-case name, no extension (e.g. "orchard-at-dusk").
- aspect: "square" | "landscape" | "portrait" | "wide" | "tall". Default square.

Examples:
- GenerateImage(prompt="A red bicycle leaning on a whitewashed wall, morning light", filename="red-bicycle")
- GenerateImage(prompt="Minimal line-art fox, single continuous stroke, black on white", filename="line-fox", aspect="portrait")

Costs money per image and is metered to the workspace. One call, one image.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "What the image should depict.",
            },
            "filename": {
                "type": "string",
                "description": "Short kebab-case name, no extension.",
            },
            "aspect": {
                "type": "string",
                "enum": ["square", "landscape", "portrait", "wide", "tall"],
                "description": "Shape of the image. Default square.",
            },
        },
        "required": ["prompt", "filename"],
    },
}


#: Aspect name → (width, height). The driver maps these to the vendor's own
#: ratio vocabulary; naming them here keeps the vendor's spelling out of the
#: model-facing schema (a member's lane should never learn "16:9" is a Gemini
#: string).
_ASPECTS: dict[str, tuple[int, int]] = {
    "square": (1024, 1024),
    "landscape": (1024, 768),
    "portrait": (768, 1024),
    "wide": (1280, 720),
    "tall": (720, 1280),
}

#: Filenames reach a path, and a path reaches the substrate. Model output is
#: UNTRUSTED INPUT (the `decompose.py` rule, same reasoning): strip anything
#: that could traverse or collide before it becomes a workspace path.
_SAFE_NAME = re.compile(r"[^a-z0-9-]+")


def _safe_filename(raw: str) -> str:
    name = _SAFE_NAME.sub("-", (raw or "").strip().lower()).strip("-")
    name = re.sub(r"-{2,}", "-", name)
    return (name or "generated")[:64]


async def handle_generate_image(auth: Any, input: dict) -> dict:
    """Render one image via the kernel's server and land it as a revision.

    Returns the `{success, path, ...}` shape every artifact verb returns, so
    `artifact_path_from` renders the member's card with no special-casing.
    A failure returns `success: False` with a member-readable `error` — never
    a placeholder that composes as though it worked (ADR-568 D2.b).
    """
    from services.capabilities import GenerationUnavailable, serve_generation

    prompt = (input.get("prompt") or "").strip()
    if not prompt:
        return {"success": False, "error": "prompt is required"}

    width, height = _ASPECTS.get((input.get("aspect") or "square").strip().lower(),
                                 _ASPECTS["square"])
    path = f"/workspace/uploads/generated/{_safe_filename(input.get('filename'))}.png"

    try:
        backend = serve_generation()
    except GenerationUnavailable as exc:
        # The typed refusal (D2.b). The member sees WHY, in their own terms,
        # rather than receiving a placeholder and discovering the gap later.
        logger.warning("[GENERATE-IMAGE] unavailable (%s): %s", exc.reason, exc)
        return {
            "success": False,
            "error": {
                "no_provider_key": "Image generation isn't configured on this deployment yet.",
                "unpriced": "Image generation is unavailable: the engine has no configured price.",
                "upstream_refused": "The image provider declined the request (account or quota).",
            }.get(exc.reason, "Image generation is unavailable."),
            "reason": exc.reason,
        }
    except ValueError as exc:  # unknown server — a config error, surfaced not swallowed
        logger.error("[GENERATE-IMAGE] misconfigured: %s", exc)
        return {"success": False, "error": "Image generation is misconfigured on this deployment."}

    try:
        asset = backend.generate(prompt=prompt, width=width, height=height)
    except Exception as exc:  # vendor failure is WEATHER — report, never placeholder
        logger.warning("[GENERATE-IMAGE] provider call failed: %s", exc)
        return {"success": False, "error": f"The image provider failed: {exc}"}

    from services.authored_substrate import write_revision
    from services.supabase import get_service_client
    from services.telemetry import image_generation_cost_usd, record_execution_event

    service = get_service_client()

    # The rented call is ALREADY SPENT by the time we get here, so it is metered
    # before the write — a substrate failure below must not also lose the bill.
    # ADR-396's one-meter invariant: `serve_generation` refuses an engine with no
    # `_IMAGE_RATES` row precisely so this lookup cannot come back empty on a
    # call that ran (D2.b `unpriced`), which makes a None here a real defect
    # rather than a free image.
    cost = image_generation_cost_usd(asset["model"])
    if cost:
        try:
            record_execution_event(
                service,  # service-role only (RLS 42501) — never auth.client
                user_id=auth.user_id,
                # ADR-373/445: attribute the spend to the principal who asked,
                # so it lands in spend_by_principal and counts against their cap.
                principal_id=getattr(auth, "principal_id", None) or auth.user_id,
                slug="generate-image",
                mode="mechanical",
                trigger_type="manual",
                status="success",
                model=asset["model"],
                cost_override_usd=cost,
            )
        except Exception:  # noqa: BLE001 — never lose the image over the ledger
            # ERROR, not warning: an unrecorded rented call is unbilled spend —
            # a correctness failure of the one-meter invariant, not a telemetry
            # inconvenience (the `compose.py` leaf-write rule, same reasoning).
            logger.error(
                "[GENERATE-IMAGE] LEDGER DROP — $%.4f of rented generation "
                "is unrecorded spend", cost,
            )
    else:
        logger.error(
            "[GENERATE-IMAGE] UNPRICED model %r rendered an image — the "
            "availability gate should have refused it; this call is unbilled",
            asset["model"],
        )

    # ⚠️ SERVICE CLIENT, deliberately. Image bytes always take the BINARY lane
    # (a PNG never utf-8-decodes), and the binary lane writes the private
    # `workspace-cas` bucket, which carries NO `storage.objects` policy by
    # design — migration 219: "service-role only". A member JWT is 403'd there
    # with "new row violates row-level security policy", which is exactly what
    # shipped: every chat-initiated generation failed AFTER paying the vendor.
    # Every other binary writer already swaps here (`apps/images/compose.py`,
    # `routes/documents.py` upload, `design_system_import.py`); this one did
    # not, and the lane hands primitives the member's JWT client (ADR-467).
    #
    # This does NOT widen the member's reach: the path is a fixed
    # `uploads/generated/` name this function builds, never caller-supplied,
    # and attribution stays the member's via `authored_by` + `user_id`.
    revision_id = write_revision(
        service,
        user_id=auth.user_id,
        path=path,
        workspace_id=getattr(auth, "workspace_id", None),
        content_bytes=asset["data"],
        content_type=asset["content_type"],
        authored_by=f"member:{auth.user_id}",
        message=f"Generated image — {prompt[:80]}",
    )

    logger.info(
        "[GENERATE-IMAGE] %s via %s (%dx%d) -> %s",
        _safe_filename(input.get("filename")), asset["model"], width, height, path,
    )
    return {
        "success": True,
        "path": path,
        # Provenance rides the result (ADR-468 D4): a leaf always says which
        # engine made it, even though the CALLER never chose one.
        "model": asset["model"],
        "revision_id": revision_id,
    }


__all__ = ["GENERATE_IMAGE_TOOL", "handle_generate_image"]
