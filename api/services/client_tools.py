"""Client tools — a lane tool the member's own machine performs (ADR-662 D6/D15).

The lane turn stays ONE streamed request. When the model calls a client tool,
the loop (`lane_runner.run_lane_turn_stream`) yields a `client_tool` frame to
the stream and awaits the result here; the yarnnn Chrome extension performs the
act — asked by yarnnn on the web in that Chrome, or relayed by the desktop app
over native messaging — and the page posts the result to
`POST /api/lanes/{lane_id}/tool-results/{call_id}` (`routes/lanes.py`), which
calls `resolve`. The same turn then continues — one lane runner, one
attribution stamp, one receipt path.

Four properties, each asserted by `api/test_adr662_local_hands.py`:

- **Offered only to a page with an executor on that machine** (`offered`): the
  page asked, AND either it runs in the desktop app on a host at or above the
  feature's minimum, or it declared the yarnnn Chrome extension in the same
  Chrome (`executor: "extension/X.Y.Z"`, ADR-662 D15). A page with neither
  never holds these tools. The declaration is a claim, not a proof: a page that
  lies gets tools nothing performs, and every act fails closed.
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
import re
import secrets
from dataclasses import dataclass, field
from typing import Any, Optional

from services.desktop_client import BROWSER_MIN_VERSION, host_meets
from services.primitives.browser import BROWSER_TOOL_NAMES, BROWSER_TOOLS

#: How long one act may take on the member's machine: the extension's consent
#: question (it waits up to 120 s for the member's answer) plus a page load.
ACT_TIMEOUT_S = 150.0

#: A job in a browser is dozens of acts; the lane's 8-round ceiling is a chat
#: ceiling (ADR-662 D8: "a silent ceiling is the wrong one"). The turn says so
#: when it reaches this.
HANDS_MAX_ROUNDS = 30

#: ADR-662 D15 — the first extension that performs the browser tools.
EXTENSION_MIN_VERSION = "0.1.0"

_EXTENSION = re.compile(r"^extension/(\d+)\.(\d+)\.(\d+)$")

#: The client-tool families a page may ask for: the desktop host's minimum and
#: the extension's minimum for each (either executor performs the family).
FAMILIES: dict[str, tuple[str, str, tuple[dict, ...]]] = {
    "browser": (BROWSER_MIN_VERSION, EXTENSION_MIN_VERSION, BROWSER_TOOLS),
}


def _extension_meets(executor: Optional[str], minimum: str) -> bool:
    m = _EXTENSION.match((executor or "").strip())
    return bool(m) and tuple(int(g) for g in m.groups()) >= tuple(int(p) for p in minimum.split("."))

CLIENT_TOOL_NAMES = frozenset(BROWSER_TOOL_NAMES)


def offered(
    client_header: Optional[str],
    requested: Optional[list[str]],
    executor: Optional[str] = None,
) -> tuple[dict, ...]:
    """The client tools this turn holds: the families the page asked for that
    an executor on its machine performs — the desktop host (by
    `X-Yarnnn-Client`) or the Chrome extension (by the declared `executor`)."""
    tools: list[dict] = []
    for family in requested or []:
        entry = FAMILIES.get(family)
        if entry and (host_meets(client_header, entry[0]) or _extension_meets(executor, entry[1])):
            tools.extend(entry[2])
    return tuple(tools)


@dataclass
class _Turn:
    user_id: str
    acts: dict[str, asyncio.Future] = field(default_factory=dict)
    #: ADR-666 D6 — stopped from outside the turn (the run's Stop). The act in
    #: flight answers "stopped" and the loop ends the turn.
    stopped: bool = False


#: nonce → the turn it belongs to. See the module note on the single worker.
_TURNS: dict[str, _Turn] = {}
#: run id → the nonce of the turn performing it (ADR-666). Same process caveat.
_RUNS: dict[str, str] = {}

#: What an act answers when its run was stopped.
STOPPED_RESULT = {
    "success": False,
    "error": "stopped",
    "receipt": "Stopped — the run was stopped before this step finished.",
}


def open_turn(user_id: str) -> str:
    """Mint the nonce for one turn that holds client tools."""
    nonce = secrets.token_urlsafe(18)
    _TURNS[nonce] = _Turn(user_id=user_id)
    return nonce


def close_turn(nonce: str) -> None:
    """End a turn: every act still waiting fails closed."""
    turn = _TURNS.pop(nonce, None)
    for run_id in [r for r, n in _RUNS.items() if n == nonce]:
        _RUNS.pop(run_id, None)
    if turn:
        for fut in turn.acts.values():
            if not fut.done():
                fut.cancel()


def bind_run(nonce: str, run_id: str) -> None:
    """ADR-666 — this turn performs that run, so the run's Stop can reach it."""
    if nonce in _TURNS:
        _RUNS[run_id] = nonce


def stop_run(run_id: str) -> bool:
    """ADR-666 D6 — stop the turn performing a run: the act in flight answers
    `STOPPED_RESULT` now, and `stopped` tells the loop to end the turn. False
    when no turn in this process performs it (it already ended)."""
    turn = _TURNS.get(_RUNS.get(run_id, ""))
    if turn is None:
        return False
    turn.stopped = True
    for fut in turn.acts.values():
        if not fut.done():
            fut.set_result(dict(STOPPED_RESULT))
    return True


def stopped(nonce: Optional[str]) -> bool:
    turn = _TURNS.get(nonce or "")
    return bool(turn and turn.stopped)


def expect(nonce: str, call_id: str) -> asyncio.Future:
    """Register an act before its frame is sent, so a fast answer is never lost."""
    fut = asyncio.get_running_loop().create_future()
    _TURNS[nonce].acts[call_id] = fut
    return fut


async def wait(nonce: str, call_id: str, fut: asyncio.Future) -> dict:
    """The executor's result for one act, or a failure the model can read."""
    try:
        return await asyncio.wait_for(fut, ACT_TIMEOUT_S)
    except asyncio.TimeoutError:
        # The sentence reaches the model and the run's steps: it names the
        # executor that exists (ADR-662 D15 — the extension in the member's
        # browser), not the desktop app it once did (audit 2026-09-24 F9).
        return {
            "success": False,
            "error": "no_answer",
            "receipt": "The browser did not answer in time — nothing is known to have changed.",
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

#: What the member reads when the run was stopped from outside the turn.
STOPPED_SENTENCE = (
    "I stopped: the run was stopped. The page is as the last finished step left it."
)

#: What the member reads when the turn reaches HANDS_MAX_ROUNDS.
ROUNDS_SENTENCE = (
    "I reached this turn's step limit in the browser before finishing. The page is as "
    "the last step left it — say continue and I will pick up from there."
)
