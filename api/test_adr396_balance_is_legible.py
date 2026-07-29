"""ADR-396 §10 gate — the prepaid balance is legible in dollars.

The 2026-07-29 billing-pane audit found the display layer still speaking the
allowance vocabulary ADR-490 §1③ retired. Two of the three meter branches were
structurally unreachable (both required `allowance > 0`, which no tier grants),
and the surviving branch's copy was hardcoded "You're on the free plan" — shown
to a live `starter` workspace holding $36.93, above a chooser asking it to pick
between $5 and $50 while rendering "0% used".

This gate defends the corrected model. It is deliberately SOURCE-shaped for the
FE half (the model lives in TypeScript; there is no Python to call) and
BEHAVIOURAL for the API half — the checkout rounding is real Python and gets a
real assertion, per [[feedback_config_gate_is_not_evidence]].

  1. MODEL COLLAPSE: the three-mode meter is DELETED, not flagged off — no
     `deriveUsageMeter` / `UsageMeter` / allowance-mode survivors anywhere in
     web/. One exported model (`deriveBalance`) with one shape.
  2. NO ALLOWANCE VOCABULARY: the three billing surfaces never tell an operator
     their usage draws an "allowance", and never offer "upgrade" as the remedy
     for an exhausted balance (false under ADR-490 — the plan buys SEATS only).
  3. ONE MODEL, THREE SURFACES: SubscriptionCard + UsagePaneBody + UserMenu all
     read `deriveBalance`, so they cannot disagree (Singular Implementation).
  4. GATE PARITY: the rendered figure is the server's netted `balance_usd` —
     the same number `check_draw` enforces — not a re-derived percentage.
  5. CHECKOUT ROUNDING (behavioural): `int(amount) * 100` truncated fractional
     dollars (a $12.99 top-up charged $12.00). Asserts the arithmetic ROUNDS.
  6. ADR: the §10 amendment exists and is Accepted.

Usage:
    cd api
    python3 test_adr396_balance_is_legible.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PASSED = 0
FAILED = 0

WEB = Path(__file__).parent.parent / "web"
USAGE_TS = WEB / "lib" / "subscription" / "usage.ts"
CARD = WEB / "components" / "subscription" / "SubscriptionCard.tsx"
PANE = WEB / "components" / "subscription" / "UsagePaneBody.tsx"
MENU = WEB / "components" / "shell" / "UserMenu.tsx"


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


def _strip_comments(src: str) -> str:
    """Drop /* */ and // comments. A gate that greps prose punishes the very
    commentary that documents the fix — the invariant is about what the operator
    READS, so the assertion must look at rendered content only."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"^\s*//.*$", "", src, flags=re.M)


def _rendered_strings(src: str) -> list[str]:
    """Copy the operator can actually see: quoted string literals plus JSX text
    nodes (the prose between > and <)."""
    out = re.findall(r'"([^"\n]{4,})"', src)
    out += re.findall(r"'([^'\n]{4,})'", src)
    out += [
        t.strip()
        for t in re.findall(r">([^<>{}\n]{4,})<", src)
        if t.strip()
    ]
    return out


def _web_sources() -> list[tuple[Path, str]]:
    """Every .ts/.tsx under web/, excluding build output + deps. The invariant is
    'nowhere in the app', so the sweep must walk the tree — a gate scoped to one
    file cannot defend an every-call-site claim."""
    out: list[tuple[Path, str]] = []
    for p in WEB.rglob("*.ts*"):
        parts = set(p.parts)
        if ".next" in parts or "node_modules" in parts:
            continue
        try:
            out.append((p, p.read_text()))
        except Exception:
            continue
    return out


def main() -> int:
    sources = _web_sources()
    print(f"\n[sweep] {len(sources)} web sources walked")

    # ── 1. The three-mode meter is DELETED ───────────────────────────────────
    print("\n[collapse] the unreachable allowance/overage branches are gone")
    for symbol in ("deriveUsageMeter", "UsageMeterMode"):
        hits = [str(p.relative_to(WEB)) for p, s in sources if symbol in s]
        check(f"no `{symbol}` survivor", not hits, ", ".join(hits[:3]))
    # `UsageMeter` as a bare type name (not a substring of another identifier).
    meter_ty = [
        str(p.relative_to(WEB))
        for p, s in sources
        if re.search(r"\bUsageMeter\b", s)
    ]
    check("no `UsageMeter` type survivor", not meter_ty, ", ".join(meter_ty[:3]))

    usage_src = USAGE_TS.read_text()
    check("`deriveBalance` is the exported model", "export function deriveBalance" in usage_src)
    check("`BalanceReadout` is the one shape", "export interface BalanceReadout" in usage_src)
    check("no `mode:` discriminant survives the collapse", "mode:" not in usage_src)
    check("dead TIER_ALLOWANCE_USD constant removed", "TIER_ALLOWANCE_USD" not in usage_src)

    # ── 2. The allowance vocabulary is gone from the billing surfaces ────────
    print("\n[copy] no surface tells the operator their usage draws an allowance")
    # Only RENDERED STRINGS matter — the word survives legitimately in the wire
    # field (`allowance_usd`, folded into the pool) and in retirement commentary.
    # So scan JSX text + quoted copy, not every line mentioning the word: a
    # comment explaining WHY the allowance retired is the opposite of the defect.
    for path in (CARD, PANE, USAGE_TS):
        src = path.read_text()
        name = path.name
        stripped = _strip_comments(src)
        offenders = [
            s for s in _rendered_strings(stripped)
            if "allowance" in s.lower()
        ]
        check(f"{name}: no operator-facing 'allowance' copy", not offenders,
              (offenders[0][:70] if offenders else ""))

    card_src = CARD.read_text()
    check("exhausted-balance remedy is 'Top up', not 'Upgrade'",
          "Top up to resume" in card_src and "Upgrade or top up to resume" not in card_src)
    check("'draws on the balance' replaces 'draws on the allowance'",
          "draws on the balance" in card_src and "draws on the allowance" not in card_src)
    check("no hardcoded 'You're on the free plan' meter copy",
          "on the free plan" not in usage_src)

    # ── 3. One model, three surfaces ─────────────────────────────────────────
    print("\n[singular] all three billing surfaces read the one model")
    for path in (CARD, PANE, MENU):
        src = path.read_text()
        check(f"{path.name} imports deriveBalance",
              "deriveBalance" in src and "@/lib/subscription/usage" in src)

    # ── 4. The rendered figure is the gate's own number ──────────────────────
    print("\n[parity] the figure shown is the figure check_draw enforces")
    check("model consumes the server-netted balance_usd",
          "balance_usd: number" in usage_src and "limits.balance_usd" in usage_src)
    check("SubscriptionCard forwards balance_usd from /user/limits",
          "balance_usd: d.balance_usd" in card_src)
    usage_code = _strip_comments(usage_src)
    check("no percentage re-derivation of the pool",
          "spend + topups" not in usage_code
          and not any("% used" in s for s in _rendered_strings(usage_code)))

    # ── 4b. The chooser and the charge are different OBJECT CLASSES ──────────
    # 2026-07-30 operator feedback: rendered as `Button`s, the amount options and
    # the confirm CTA shared a pill shape and sat in one flow — five similar pills
    # where two meant entirely different things (pick an amount vs. charge my
    # card). A selection is a CARD; an action is a BUTTON. Guarding the shape
    # keeps a future refactor from collapsing them back together.
    print("\n[affordance] the amount selection is a card, the charge is a button")
    chooser = re.search(
        r'role="radiogroup"\s+aria-label="Top-up amount".*?(?=\{topupChoice === "custom")',
        card_src, re.S,
    )
    check("top-up radiogroup found", chooser is not None)
    if chooser:
        body = chooser.group(0)
        check("amount options are not <Button> pills", "<Button" not in body)
        check("selected option carries a ring cue", "ring-primary" in body)
        check("options render as bordered cards", "rounded-lg border" in body)
    check("the charge sits across a divider from the selection",
          "border-t border-border pt-4" in card_src)
    check("the CTA still names its amount",
          "`Add ${formatUsd(topupUsd)}`" in card_src)

    # ── 5. Checkout rounding — BEHAVIOURAL ───────────────────────────────────
    print("\n[behavioural] the top-up charge rounds, never truncates")
    sub_src = (Path(__file__).parent / "routes" / "subscription.py").read_text()
    # Strip Python comments — the fix's own note QUOTES the removed expression.
    sub_code = re.sub(r"^\s*#.*$", "", sub_src, flags=re.M)
    check("truncating `int(amount) * 100` is gone", "int(amount) * 100" not in sub_code)
    m = re.search(r"custom_price_cents = (.+)", sub_code)
    check("custom_price_cents expression found", m is not None)
    if m:
        expr = m.group(1).strip()
        # Evaluate the ACTUAL expression against fractional dollars — the bug was
        # arithmetic, so the assertion must be arithmetic.
        def cents(amount: float) -> int:
            return int(eval(expr, {"int": int, "round": round, "float": float}, {"amount": amount}))
        check("$12.99 → 1299 cents (was 1200)", cents(12.99) == 1299, f"got {cents(12.99)}")
        check("$25 → 2500 cents (whole dollars unchanged)", cents(25) == 2500, f"got {cents(25)}")
        check("$5 → 500 cents (the floor)", cents(5) == 500, f"got {cents(5)}")

    # ── 6. The ADR amendment exists ──────────────────────────────────────────
    print("\n[adr] the §10 amendment is on the record")
    adrs = list((Path(__file__).parent.parent / "docs" / "adr").glob("ADR-396*.md"))
    check("ADR-396 found", len(adrs) == 1)
    if adrs:
        adr = adrs[0].read_text()
        check("§10 amendment section present",
              "## 10. Amendment (2026-07-29)" in adr)
        check("amendment is Accepted", re.search(r"## 10\..*?\*\*Status\*\*: Accepted", adr, re.S) is not None)
        check("amendment preserves the no-credit-currency ruling",
              "§3's no-credit-currency ruling, and §5's double-charge invariant are untouched" in adr
              or "no-credit-currency" in adr)

    print(f"\n{'='*60}\nADR-396 §10 gate: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
