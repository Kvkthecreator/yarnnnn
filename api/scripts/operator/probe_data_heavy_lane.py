"""Can a lane answer a question that needs a WHOLE dataset? — the four-walls probe.

The substrate holds 5 CSVs, largest 372 chars. So the data path has NEVER been
driven, and four ceilings sit un-exercised in both directions:

  1. READ CAP      `READ_FILE_MAX_CHARS = 100_000` (primitives/workspace.py)
  2. HISTORY       `_HISTORY_MAX_CHARS  = 120_000` (routes/lanes.py)
  3. SEARCH        `.ilike(...).limit(80)` — substring over whole files, no rows
  4. WRITE         whole-content revisions (no append grain)

The failure this probe exists to catch is NOT an error. It is a lane that reads
the first window, answers confidently from ~12% of the data, and sounds right.
So the probe plants facts the agent CANNOT guess and CANNOT reach from a
partial read, then scores the ANSWER against ground truth computed here in
Python — never the transcript, never the agent's own claim about its work.

Three questions, chosen so each isolates one wall:

  Q1 ROW COUNT     — needs the whole file. A partial read answers ~500.
  Q2 TAIL FACT     — the planted row sits at ~92% depth, past every early window.
  Q3 AGGREGATE     — a sum over one column; wrong if any rows are unseen.

Each is scored PASS/FAIL against a value computed from the same bytes the file
was written from. A lane that never reads the tail cannot pass Q2 by luck: the
planted client name is a nonsense token that appears exactly once.

Run:  python3 api/scripts/operator/probe_data_heavy_lane.py
"""

from __future__ import annotations

import asyncio
import csv
import io
import os
import random
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(API))

for _line in (API / ".env").read_text().splitlines():
    if _line.strip() and not _line.strip().startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

os.environ.setdefault("MODEL_ROUTER_ENABLED", "1")
os.environ.setdefault("LANES_ENABLED", "1")

from services.authored_substrate import write_revision  # noqa: E402
from services.lane_runner import run_lane_turn  # noqa: E402
from services.primitives.workspace import READ_FILE_MAX_CHARS  # noqa: E402
from services.supabase import AuthenticatedClient, get_service_client  # noqa: E402

WORKSPACE_ID = "d5b9029b-bd4e-4757-9fcb-e2b139fd4913"
PROBE_ROOT = "operation/_probe-data-heavy"
CSV_LEAF = f"{PROBE_ROOT}/pipeline.csv"

ROWS = 5000
#: The planted tail fact. A nonsense token so it cannot be guessed, inferred
#: from context, or confused with a real row. Placed deep on purpose.
NEEDLE_CLIENT = "Zorvathic Dynamics"
NEEDLE_AT = 4600  # ~92% depth — past the first read window by a wide margin

STAGES = ["prospect", "qualified", "negotiation", "won", "lost"]
_RNG = random.Random(20260917)  # deterministic; seed chosen so the needle stage
                                # is NOT "won" — Q3 discusses "won", and a "won"
                                # needle would let Q2 pass on Q3's prose alone.


def build_csv() -> tuple[str, dict]:
    """The dataset, plus the ground truth computed FROM THE SAME BYTES.

    Truth is derived here, not asserted: the probe cannot disagree with its own
    fixture. Every scored value comes out of this dict.
    """
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["id", "client", "stage", "amount", "owner", "last_contact"])
    rows = []
    for i in range(1, ROWS + 1):
        client = NEEDLE_CLIENT if i == NEEDLE_AT else f"Client {i:05d} Holdings"
        stage = STAGES[_RNG.randrange(len(STAGES))]
        amount = _RNG.randrange(1_000, 500_000)
        owner = f"rep{_RNG.randrange(1, 9)}"
        last = f"2026-{_RNG.randrange(1, 10):02d}-{_RNG.randrange(1, 29):02d}"
        rows.append([i, client, stage, amount, owner, last])
        w.writerow(rows[-1])
    content = out.getvalue()

    needle = rows[NEEDLE_AT - 1]
    truth = {
        "total_rows": ROWS,
        "needle_client": NEEDLE_CLIENT,
        "needle_stage": needle[2],
        "needle_amount": needle[3],
        "won_total": sum(r[3] for r in rows if r[2] == "won"),
        "won_count": sum(1 for r in rows if r[2] == "won"),
        "chars": len(content),
    }
    return content, truth


def _nums(text: str) -> list[int]:
    """Every integer in the answer, commas stripped — the scorer's alphabet."""
    return [int(m.replace(",", "")) for m in re.findall(r"\d[\d,]*", text or "")]


def score(answer: str, truth: dict) -> dict:
    """PASS/FAIL per question, against values the agent cannot guess.

    Tolerances are deliberate, not generous:
      Q1 exact — a row count is a fact, not an estimate.
      Q2 exact on BOTH the stage word and the amount — the row or nothing.
      Q3 within 1% — allows arithmetic slips, NOT a partial-data sum (which
         would land near 12% of truth, the first-window fraction).
    """
    text = answer or ""
    low = text.lower()
    nums = _nums(text)

    q1 = truth["total_rows"] in nums

    saw_needle = NEEDLE_CLIENT.lower() in low
    q2 = saw_needle and truth["needle_stage"] in low and truth["needle_amount"] in nums

    won = truth["won_total"]
    q3 = any(abs(n - won) <= won * 0.01 for n in nums)

    return {
        "q1_row_count": q1,
        "q2_tail_fact": q2,
        "q2_saw_needle_at_all": saw_needle,
        "q3_aggregate": q3,
        "answer_chars": len(text),
    }


async def main() -> None:
    service = get_service_client()
    owner = (
        service.table("workspaces").select("owner_id")
        .eq("id", WORKSPACE_ID).limit(1).execute().data or []
    )
    if not owner:
        print(f"FAIL: workspace {WORKSPACE_ID} not found")
        sys.exit(1)
    user_id = owner[0]["owner_id"]
    auth = AuthenticatedClient(client=service, user_id=user_id, workspace_id=WORKSPACE_ID)

    # Purge first — a stale CSV from a prior run would let the lane answer from
    # someone else's dataset, and the needle would still match.
    stale = (
        service.table("workspace_files").select("id")
        .eq("user_id", user_id).like("path", f"/workspace/{PROBE_ROOT}/%")
        .execute().data or []
    )
    for row in stale:
        service.table("workspace_files").delete().eq("id", row["id"]).execute()
    print(f"purged {len(stale)} stale probe row(s)")

    content, truth = build_csv()
    write_revision(
        service, user_id=user_id, path=f"/workspace/{CSV_LEAF}",
        content=content, authored_by="operator", author_identity_uuid=user_id,
        message="probe: 5000-row pipeline", lifecycle="active",
    )

    windows = -(-truth["chars"] // READ_FILE_MAX_CHARS)  # ceil
    print()
    print(f"dataset: {truth['chars']:,} chars, {truth['total_rows']:,} rows")
    print(f"read cap: {READ_FILE_MAX_CHARS:,} chars -> {windows} full windows to see it all")
    print(f"first window covers ~{READ_FILE_MAX_CHARS / truth['chars']:.0%} of the file")
    print(f"needle: {NEEDLE_CLIENT!r} at row {NEEDLE_AT} "
          f"(~{NEEDLE_AT / ROWS:.0%} depth), stage={truth['needle_stage']}, "
          f"amount={truth['needle_amount']:,}")
    print(f"truth: won_total={truth['won_total']:,} over {truth['won_count']:,} rows")
    print()

    question = (
        f"Open {CSV_LEAF} — it is our sales pipeline. Answer all three, precisely:\n"
        f"1. Exactly how many deal rows are in the file (excluding the header)?\n"
        f"2. There is a client called '{NEEDLE_CLIENT}'. What stage is that deal "
        f"in, and what is its amount?\n"
        f"3. What is the total amount of all deals in stage 'won'?"
    )

    model = "anthropic/claude-sonnet-5"
    print(f"model={model}")
    print("asking...")
    res = await run_lane_turn(
        auth, model=model, history=[], user_message=question, member_label="Kevin",
    )

    answer = res.get("text") or ""
    tools = [t.get("name") if isinstance(t, dict) else str(t)
             for t in res.get("tools_called", [])]
    s = score(answer, truth)

    print()
    print(f"success={res.get('success')} rounds={res.get('rounds')} "
          f"tokens_in={res.get('tokens_in')} tokens_out={res.get('tokens_out')}")
    print(f"tools ({len(tools)}): {tools}")
    if not res.get("success"):
        print(f"lane error: {res.get('error')} — {res.get('message')}")

    print()
    print("ANSWER (what the member would read):")
    print("-" * 68)
    print(answer[:2500])
    print("-" * 68)

    print()
    print("SCORED against ground truth (not the transcript):")
    print(f"  Q1 row count  ({truth['total_rows']:,})            -> "
          f"{'PASS' if s['q1_row_count'] else 'FAIL'}")
    print(f"  Q2 tail fact  ({truth['needle_stage']}/{truth['needle_amount']:,}) -> "
          f"{'PASS' if s['q2_tail_fact'] else 'FAIL'}"
          f"   (named the client at all: {s['q2_saw_needle_at_all']})")
    print(f"  Q3 won total  ({truth['won_total']:,})        -> "
          f"{'PASS' if s['q3_aggregate'] else 'FAIL'}")

    passed = sum(1 for k in ("q1_row_count", "q2_tail_fact", "q3_aggregate") if s[k])
    print()
    print(f"VERDICT: {passed}/3 correct.")
    # The finding that matters is not the score — it is whether a WRONG answer
    # arrived sounding right. That is the silent wall.
    hedged = any(w in answer.lower() for w in
                 ("truncated", "portion", "not all", "only the first",
                  "unable to see", "rest of the file", "partial",
                  # The 2026-09-16 cut-off notice (_TRUNCATED_ANSWER_NOTICE).
                  # A spoken failure is NOT a silent one — without this the
                  # probe would report its own fix as the defect.
                  "ran out of room", "length limit"))
    print(f"Answer acknowledged incompleteness: {hedged}")
    if not answer.strip():
        print(">>> EMPTY MESSAGE — the member sees nothing at all.")
    elif passed < 3 and not hedged:
        print(">>> SILENT WRONG ANSWER — the failure mode the probe exists to catch.")
    elif passed < 3:
        print("Incomplete, but the turn SAID SO — the honest failure.")


if __name__ == "__main__":
    asyncio.run(main())
