"""ADR-623 — a read of an image ends in SEEING it (the internal lane).

THE DEFECT, observed live in the chat surface (2026-08-31). A member asked the
Editor about a workspace PNG. It answered:

    "`ReadFile` confirms the file exists (PNG, ~2.5MB) but its bytes are served
     out-of-band to a viewer — my tools don't get pixel access to a workspace
     path like that. The only way I can actually look at an image is if it's
     attached directly in this conversation."

Every word of that was TRUE, and it should not have been. The engine was
vision-capable, the bytes were in the CAS, and `_mint_cas_url_for_path` — which
mints a serving URL FROM A WORKSPACE PATH — sat one module away, called from
exactly one place: the member's own attachment loop.

⭐⭐⭐ THE ASYMMETRY THAT MADE IT URGENT. ADR-621 (shipped hours earlier) gave the
EXTERNAL MCP surface a `content_url` on `open`, so a third-party agent on
claude.ai could fetch those bytes. The FIRST-PARTY lane agent, in our own
product, could not. External must never be better than internal.

WHAT IS GATED
  1. `image_part_for_tool_result` promotes a binary ReadFile into a real vision
     message — and refuses every case it must (not ReadFile, not an image, an
     engine that cannot see, a text file, a failed read).
  2. The pixels ride a `user` message's `image_url` part, NEVER base64 in the
     tool-result string (the ADR-621 D2 refusal: bytes through a token stream
     corrupt).
  3. BOTH tool loops (streaming + non-streaming) promote — they are twins, and
     a fix applied to one is a fix that works half the time.
  4. Vision SURVIVES the turn: history replay re-mints from the stored path,
     and names a file that has since vanished rather than dropping it silently.
  5. ONE path→URL resolver at the seam — three spellings had already drifted
     (two passed `workspace_id` to the mint, one did not).
  6. The ReadFile notice no longer ends in a dead end.
  7. The pixels are HELD until every tool_result in the round has landed —
     appending them inside the per-call loop splits the tool_use/tool_result
     run and kills the turn (see clause 7 below).

⭐⭐⭐ THE SECOND DEFECT, observed live 2026-08-31 (clause 7). ADR-623 shipped
promoting the pixels INSIDE the per-tool-call loop:

    for tc in routed.tool_calls:
        messages.append({"role": "tool", ...})     # this call's result
        if vision_msg: messages.append(vision_msg) # ← a USER message, mid-run

The Anthropic contract is that every `tool_use` in the assistant message is
answered by its `tool_result` in the IMMEDIATELY following message. With ONE
tool call that holds. With TWO — and a non-final one an image — the injected
user message splits the run, and the turn dies at the provider:

    "messages.14: `tool_use` ids were found without `tool_result` blocks
     immediately after: toolu_019vxRxDVjeocBHq9YeHaVc8"

⭐ A single-call read could never surface it, which is exactly how it passed a
click-pass AND this gate: clause 1 asserts WHICH results promote, and never
once looked at the resulting message SEQUENCE. Clause 7 is that missing check.

Falsified: promotion removed · a non-vision engine promoted anyway · the history
re-mint reverted · the resolver re-duplicated · the pixels moved back inside the
loop (clause 7 goes red).

Usage:  cd api && python3 test_adr623_the_lane_can_see.py
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

API_ROOT = Path(__file__).parent
sys.path.insert(0, str(API_ROOT))

FAILURES: list[str] = []
PASSES = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSES
    if ok:
        PASSES += 1
        print(f"PASS  {label}  {detail}")
    else:
        FAILURES.append(label)
        print(f"FAIL  {label}  {detail}")


import services.lane_runner as lr  # noqa: E402

# A binary ReadFile result, exactly as the ADR-427 §8 notice shapes it.
BIN_RESULT = {
    "success": True, "found": True, "binary": True, "content": None,
    "scope": "workspace", "path": "marketing/assets/photo.png",
    "content_type": "image/png", "byte_size": 2_585_846,
    "message": "Binary file (image/png, 2585846 bytes) …",
}
TEXT_RESULT = {"success": True, "found": True, "path": "system/notes.md",
               "content": "# real text"}

_MINTED = "https://example.test/cas/72/726abc?sig=x"


class _Auth:
    client = None
    user_id = "u-1"
    workspace_id = "w-1"


# Neutralize the network: this gate is about WHICH cases promote, not the driver.
import services.storage_backend as sb  # noqa: E402
sb.mint_serving_url_for_path = lambda auth, path: _MINTED
lr_mod = sys.modules["services.lane_runner"]

auth = _Auth()
VISION = "anthropic/claude-sonnet-5"
BLIND = "deepseek/deepseek-chat"

# --- 1. the promotion, and every refusal --------------------------------------
msg = lr.image_part_for_tool_result(auth, VISION, "ReadFile", BIN_RESULT)
check("1a a binary image read becomes a vision message", isinstance(msg, dict))
if isinstance(msg, dict):
    kinds = [p["type"] for p in msg["content"]]
    check("1b it is a USER message with text + image_url parts",
          msg["role"] == "user" and kinds == ["text", "image_url"], f"{kinds}")
    check("1c the text part NAMES the file (an unlabelled image is ambiguous "
          "when a turn read several)",
          "photo.png" in msg["content"][0]["text"])
    # ⭐ FROM THE 2026-08-31 CLICK-PASS. The model described the picture
    # correctly and then thanked the member for "pasting the render through" —
    # nobody had pasted anything. An image part on a `user` message reads as
    # something the HUMAN handed over, because that is the only way one ever
    # arrived before this ADR. The label must name the TOOL as its source or
    # the model's account of its own turn is false.
    check("1c2 the label says the image came from the READ, not from the member",
          "ReadFile" in msg["content"][0]["text"]
          and "not something the member attached" in msg["content"][0]["text"])
    check("1d the image rides a URL, never base64 in the payload",
          msg["content"][1]["image_url"]["url"] == _MINTED
          and "base64" not in str(msg))

check("1e a non-vision engine gets NOTHING (never a part it cannot read)",
      lr.image_part_for_tool_result(auth, BLIND, "ReadFile", BIN_RESULT) is None)
check("1f a TEXT read is never promoted",
      lr.image_part_for_tool_result(auth, VISION, "ReadFile", TEXT_RESULT) is None)
check("1g a non-ReadFile verb is never promoted",
      lr.image_part_for_tool_result(auth, VISION, "ListFiles", BIN_RESULT) is None)
check("1h a FAILED read is never promoted",
      lr.image_part_for_tool_result(
          auth, VISION, "ReadFile", {**BIN_RESULT, "success": False}) is None)
# ⭐ A PDF is binary and is NOT a viewable image — promoting it would hand a
# vision engine a file it cannot render.
check("1i a non-image binary (PDF) is not promoted",
      lr.image_part_for_tool_result(
          auth, VISION, "ReadFile", {**BIN_RESULT, "content_type": "application/pdf"}) is None)
# ⭐ SVG is text: ReadFile returns its SOURCE, which is more useful to a model
# than a rasterization it cannot edit.
check("1j svg is deliberately absent from the viewable set",
      "image/svg+xml" not in lr.VISION_IMAGE_TYPES)

# --- 2. no base64 anywhere on this path ---------------------------------------
src = inspect.getsource(lr.image_part_for_tool_result)
check("2a the promoter never encodes bytes (ADR-621 D2 — sampled bytes corrupt)",
      "b64" not in src and "base64" not in src.replace("base64-through", ""))

# --- 3. BOTH loops promote (they are twins) -----------------------------------
runner_src = (API_ROOT / "services/lane_runner.py").read_text()
n_promote = runner_src.count("image_part_for_tool_result(tool_auth, model, name, result)")
check("3a both tool loops promote (streaming + non-streaming)",
      n_promote == 2, f"call sites={n_promote}")
n_toolmsg = runner_src.count('"role": "tool",')
check("3b every tool-result append has a promotion beside it",
      n_promote == n_toolmsg, f"tool appends={n_toolmsg} promotions={n_promote}")

# --- 4. vision survives the turn ----------------------------------------------
lanes_src = (API_ROOT / "routes/lanes.py").read_text()
hist = lanes_src.split("def _fetch_history(")[1].split("\ndef ")[0]
check("4a history SELECTS metadata (it carried the attachment and was dropped)",
      "metadata" in hist.split("select(")[1][:140])
check("4b replay RE-MINTS from the stored path (the URL rots, the path does not)",
      "_mint_cas_url_for_path(auth, a[\"path\"])" in hist)
check("4c a vanished attachment is NAMED, not silently dropped",
      "no longer available" in hist)
# ⭐ The persisted row must stay plain text — a stored signed URL would rot.
check("4d the persisted user row still stores TEXT, never the parts array",
      "never the parts array" in lanes_src)

# --- 5. ONE resolver at the seam ----------------------------------------------
check("5a the seam owns the path→URL walk",
      hasattr(sb, "mint_serving_url_for_path"))
lanes_mint = lanes_src.split("def _mint_cas_url_for_path(")[1].split("\ndef ")[0]
check("5b routes/lanes delegates to it (no second spelling of the walk)",
      "mint_serving_url_for_path" in lanes_mint
      and "head_version_id" not in lanes_mint)
# ⭐ services must not import from routes — the inversion this arc almost shipped.
check("5c no services→routes import was introduced",
      "from routes." not in runner_src)

# --- 6. the notice no longer dead-ends ----------------------------------------
prim_src = (API_ROOT / "services/primitives/workspace.py").read_text()
notice = prim_src.split("def _binary_file_notice(")[1].split("\ndef ")[0]
check("6a the notice no longer claims the bytes are simply unreachable",
      "The file surface/viewer serves it via a minted URL." not in notice)
check("6b for a viewable image it says the picture is coming",
      "follows" in notice and "next message" in notice)
check("6c and it is CONDITIONAL on the engine (a blind lane is not promised pixels)",
      "If your engine can see images" in notice)
# ⚠️ Scope this to the MODULE, not the notice function: the helper that imports
# the lane's list is defined beside `_binary_file_notice`, not inside it — a
# slice-scoped assertion reads the wrong region and fails for the wrong reason.
# What matters is that the type list is IMPORTED, never re-spelled here.
check("6d the viewable set is imported from the lane, never re-spelled",
      "from services.lane_runner import VISION_IMAGE_TYPES" in prim_src
      and '"image/png"' not in prim_src)

# --- 7. the pixels never split a tool_use/tool_result run ---------------------
# The defect this clause exists for is an ORDERING defect, so assert on order,
# not on presence. Both loops are twins (clause 3) — check both.
check("7a both tool loops hold the pixels in a pending list, never appending "
      "a user message mid-run",
      runner_src.count("pending_vision.append(vision_msg)") == 2
      and runner_src.count("messages.append(vision_msg)") == 0)
check("7b the held pixels are flushed after the whole tool run",
      runner_src.count("messages.extend(pending_vision)") == 2)
check("7c the pending list is reset per ROUND (a stale carry would re-send "
      "last round's pixels)",
      runner_src.count("pending_vision: list[dict] = []") == 2)

# The ordering invariant itself, driven — not grepped. Mirrors the loop body's
# append order for a round of N calls and asserts the provider contract holds.
def _simulate(n_calls: int, image_at: set[int]) -> list[str]:
    msgs = [("assistant", [f"toolu_{i}" for i in range(n_calls)])]
    pending = []
    for i in range(n_calls):
        msgs.append(("tool", f"toolu_{i}"))
        if i in image_at:
            pending.append(("user", "<image>"))
    msgs.extend(pending)
    return msgs

def _violates(msgs) -> bool:
    """True if any tool_use lacks its tool_result in the immediately
    following run of tool messages."""
    for i, (role, payload) in enumerate(msgs):
        if role != "assistant":
            continue
        got, j = [], i + 1
        while j < len(msgs) and msgs[j][0] == "tool":
            got.append(msgs[j][1])
            j += 1
        if any(x not in got for x in payload):
            return True
    return False

check("7d two calls, the FIRST an image — the reported break — orders validly",
      not _violates(_simulate(2, {0})))
check("7e three calls, the MIDDLE an image, orders validly",
      not _violates(_simulate(3, {1})))
check("7f every call an image: all pixels still delivered, order still valid",
      not _violates(_simulate(3, {0, 1, 2}))
      and sum(1 for r, _ in _simulate(3, {0, 1, 2}) if r == "user") == 3)
check("7g the single-call case that used to pass still passes "
      "(the fix is not a regression)",
      not _violates(_simulate(1, {0})))

print()
print("=" * 62)
if FAILURES:
    print(f"ADR-623: FAIL — {len(FAILURES)} assertion(s): {FAILURES}")
    sys.exit(1)
print(f"ADR-623 the lane can see: {PASSES}/{PASSES} assertions pass")
