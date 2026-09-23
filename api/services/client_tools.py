"""Client tools — a lane tool the member's desktop app performs (ADR-662 D6).

The lane turn stays ONE streamed request. When the model calls a client tool,
the loop (`lane_runner.run_lane_turn_stream`) yields a `client_tool` frame to
the stream and awaits the result here; the desktop app performs the act in its
own browser pane and posts the result to
`POST /api/lanes/{lane_id}/tool-results/{call_id}` (`routes/lanes.py`), which
calls `resolve`. The same turn then continues — one lane runner, one
attribution stamp, one receipt path.

Four properties, each asserted by `api/test_adr662_local_hands.py`:

- **Offered only to the shell that asked** (`offered`): a turn from the desktop
  app, on a host at or above the feature's minimum, whose page said the member
  switched the browser on. The web never holds these tools.
- **Only that shell can answer**: every turn mints a nonce that rides only in
  its own stream; `resolve` refuses a wrong nonce and a different member.
- **Fails closed**: an act that is not answered within `ACT_TIMEOUT_S`, a
  stopped turn, or a recycled server ends the act — never a hang, never a
  guessed result.
- **Stops when stuck** (`StuckWatch`, ADR-662 D8): the spike burned 300–400k
  tokens repeating a refused act; the same failure twice is told to the model,
  and a run of failures ends the turn.

⚠️ The pending table lives in this process. Correct on today's single API
worker (`render.yaml`: one uvicorn process, one instance); a second worker or
instance needs it keyed somewhere shared, and the result route would 404 on
the wrong one. Recorded in ADR-662 D6.
"""

from __future__ import annotations

import asyncio
import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Optional

from services.desktop_client import BROWSER_MIN_VERSION, host_meets
from services.primitives.browser import BROWSER_TOOL_NAMES, BROWSER_TOOLS

#: How long one act may take in the app: a slow page load plus the read-back.
ACT_TIMEOUT_S = 60.0

#: A job in a browser is dozens of acts; the lane's 8-round ceiling is a chat
#: ceiling (ADR-662 D8: "a silent ceiling is the wrong one"). The turn says so
#: when it reaches this.
HANDS_MAX_ROUNDS = 30

#: The client-tool families a page may ask for, each with its host minimum.
FAMILIES: dict[str, tuple[str, tuple[dict, ...]]] = {
    "browser": (BROWSER_MIN_VERSION, BROWSER_TOOLS),
}

CLIENT_TOOL_NAMES = frozenset(BROWSER_TOOL_NAMES)


def offered(client_header: Optional[str], requested: Optional[list[str]]) -> tuple[dict, ...]:
    """The client tools this turn holds: the families the page asked for that
    its host is new enough to perform. Empty for any browser request."""
    tools: list[dict] = []
    for family in requested or []:
        entry = FAMILIES.get(family)
        if entry and host_meets(client_header, entry[0]):
            tools.extend(entry[1])
    return tuple(tools)


@dataclass
class _Turn:
    user_id: str
    acts: dict[str, asyncio.Future] = field(default_factory=dict)


#: nonce → the turn it belongs to. See the module note on the single worker.
_TURNS: dict[str, _Turn] = {}


def open_turn(user_id: str) -> str:
    """Mint the nonce for one turn that holds client tools."""
    nonce = secrets.token_urlsafe(18)
    _TURNS[nonce] = _Turn(user_id=user_id)
    return nonce


def close_turn(nonce: str) -> None:
    """End a turn: every act still waiting fails closed."""
    turn = _TURNS.pop(nonce, None)
    if turn:
        for fut in turn.acts.values():
            if not fut.done():
                fut.cancel()


def expect(nonce: str, call_id: str) -> asyncio.Future:
    """Register an act before its frame is sent, so a fast answer is never lost."""
    fut = asyncio.get_running_loop().create_future()
    _TURNS[nonce].acts[call_id] = fut
    return fut


async def wait(nonce: str, call_id: str, fut: asyncio.Future) -> dict:
    """The app's result for one act, or a failure the model can read."""
    try:
        return await asyncio.wait_for(fut, ACT_TIMEOUT_S)
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "no_answer",
            "receipt": "The desktop app did not answer in time — nothing is known to have changed.",
        }
    finally:
        turn = _TURNS.get(nonce)
        if turn:
            turn.acts.pop(call_id, None)


def resolve(nonce: str, call_id: str, user_id: str, result: Any) -> str:
    """Hand an act's result to the waiting turn. Returns "ok", or the reason
    it was refused: "unknown" (no such turn or act — it ended, or it was never
    this process's) or "not_yours" (another member's turn)."""
    turn = _TURNS.get(nonce)
    if turn is None:
        return "unknown"
    if turn.user_id != user_id:
        return "not_yours"
    fut = turn.acts.get(call_id)
    if fut is None or fut.done():
        return "unknown"
    fut.set_result(result if isinstance(result, dict) else {"success": False, "error": "bad_result"})
    return "ok"


class StuckWatch:
    """ADR-662 D8 — stop when stuck. Fed each client act's outcome in order.

    `note(...)` returns None to carry on, "warn" when the model repeated an act
    that just failed (it is told so, in the result it reads), or "stop" when
    acts have failed `STOP_AFTER` times in a row (the turn ends and says so).
    """

    STOP_AFTER = 4

    def __init__(self) -> None:
        self._last_failed: Optional[str] = None
        self._run = 0

    def note(self, name: str, arguments: Any, ok: bool) -> Optional[str]:
        key = f"{name}:{json.dumps(arguments, sort_keys=True, default=str)}"
        if ok:
            self._last_failed, self._run = None, 0
            return None
        repeated = key == self._last_failed
        self._last_failed = key
        self._run += 1
        if self._run >= self.STOP_AFTER:
            return "stop"
        return "warn" if repeated else None


#: What the model reads when it repeats a failed act.
REPEAT_NOTE = (
    "That exact act already failed once. It will not work by repeating it: "
    "read the page again, try a different element, or tell the member what is in the way."
)

#: What the member reads when the turn stops for being stuck.
STUCK_SENTENCE = (
    "I stopped: my last few steps in the browser failed, and repeating them would not "
    "have helped. The page is as the last successful step left it."
)

#: What the member reads when the turn reaches HANDS_MAX_ROUNDS.
ROUNDS_SENTENCE = (
    "I reached this turn's step limit in the browser before finishing. The page is as "
    "the last step left it — say continue and I will pick up from there."
)
