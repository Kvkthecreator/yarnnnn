"""ADR-632 — the steward retires. Script-style gate.

Pins ABSENCE where a resurrected module would silently re-wire spend, and the
two live frame RATCHETS (DP22) that replace the steward-era prompt ceilings.

Run: cd api && python3 test_adr632_the_seat_retires.py
"""
from __future__ import annotations

import os
import re
import sys

API = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(API)
WEB = os.path.join(ROOT, "web")
sys.path.insert(0, API)

_p = _f = 0


def _check(label, ok, detail=""):
    global _p, _f
    if ok:
        _p += 1; print(f"  ok   {label}")
    else:
        _f += 1; print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def _exists(rel):
    return os.path.exists(os.path.join(ROOT, rel))


print("§1 the stack is gone")
for rel in ("api/agents", "api/services/wake.py", "api/services/wake_queue.py", "api/services/wake_drainer.py",
            "api/services/wake_evaluation.py", "api/services/wake_sources", "api/services/review_rotation.py",
            "api/services/review_proposal_dispatch.py", "api/services/freddie_envelope.py",
            "api/services/freddie_chat_surfacing.py", "api/services/substrate_snapshot.py",
            "api/services/kernel_mirrors.py", "api/services/model_selection.py", "api/services/agent_gating.py",
            "api/services/recurrence.py", "api/services/recurrence_prompt_inference.py", "api/services/commands.py",
            "api/services/execution_router.py", "api/routes/feed.py",
            "api/services/primitives/fire_invocation.py", "api/services/primitives/manage_hook.py",
            "api/services/primitives/schedule.py", "api/services/primitives/mirror_calibration.py",
            "api/services/primitives/mirror_schedule_index.py", "api/services/primitives/mirror_recent_execution.py",
            "api/services/primitives/mirror_signal_state.py", "api/services/primitives/system_state.py",
            "api/services/primitives/compose.py"):
    _check(f"{rel} deleted", not _exists(rel))
_check("judgment_log.py replaces freddie_audit.py", _exists("api/services/judgment_log.py") and not _exists("api/services/freddie_audit.py"))
_check("the compose ENGINE stays (ADR-417)", _exists("api/services/compose/engine.py"))

print("§2 no live module imports a deleted one")
pat = re.compile(r"^\s*(?:from|import)\s+(?:services\.(?:wake|wake_queue|wake_drainer|wake_evaluation|wake_sources|review_rotation|review_proposal_dispatch|freddie_envelope|freddie_chat_surfacing|freddie_audit|substrate_snapshot|kernel_mirrors|model_selection|agent_gating|recurrence|recurrence_prompt_inference|commands|execution_router)\b|agents(?:\.|\s|$)|routes\.feed\b|services\.primitives\.(?:fire_invocation|manage_hook|schedule|mirror_[a-z_]+|compose|system_state)\b)", re.M)
hits = []
for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "api")):
    dirnames[:] = [d for d in dirnames if d not in ("venv", ".venv-mcp", "__pycache__", "scripts")]
    for fn in filenames:
        if not fn.endswith(".py") or fn.startswith("test_"):
            continue
        p = os.path.join(dirpath, fn)
        with open(p, encoding="utf-8") as f:
            src = f.read()
        for m in pat.finditer(src):
            hits.append(f"{os.path.relpath(p, ROOT)}: {m.group(0).strip()}")
_check("zero imports of the retired stack in live code", not hits, "; ".join(hits[:5]))

print("§3 the tick: no steward gate; strings + capture + skills unconditional")
sched = _read("api/jobs/unified_scheduler.py")
_check("no agent_gating import", "agent_gating" not in sched)
_check("no is_agent_enabled call", "is_agent_enabled(" not in sched)
_check("no recurrence dispatch", "dispatch_due_invocations" not in sched and "cron_tick" not in sched)
_check("no hook walker / queue drain / kernel mirrors", all(w not in sched for w in ("walk_hooks", "reclaim_stale_locks", "drain_all_users_with_pending", "mirror_schedule_index_for_all_users")))
_check("strings lane runs", "drain_due_string_runs(" in sched)
_check("capture lane runs behind its own flag", "is_capture_lane_enabled(" in sched and "drain_due_captures" in sched)
_check("skills mirror runs", "mirror_kernel_skills_for_all_workspaces(" in sched)

print("§4 the doors are closed")
main_src = _read("api/main.py")
_check("feed router unmounted", "feed.router" not in main_src and "import images, memory, feed" not in main_src)
_check("admin has no trigger-task door", "/trigger-task/" not in _read("api/routes/admin.py"))
ks = _read("api/services/kernel_surfaces.py")
_check("no STEWARD_SURFACE_SLUGS filter", "STEWARD_SURFACE_SLUGS" not in ks and "agent_on" not in ks)
_check("no system-agent surface row", '"slug": "system-agent"' not in ks)
_check("budget envelope has no queue_depth", "queue_depth" not in _read("api/routes/budget.py"))
_check("connector payload has no agent_enabled", "agent_enabled" not in _read("api/routes/integrations.py"))
_check("proposal insert enqueues no wake", "proposal_arrival" not in _read("api/services/primitives/propose_action.py"))
_check("init bootstraps no steward session", "thinking_partner" not in _read("api/services/workspace_init.py"))
reg = _read("api/services/primitives/registry.py")
_check("no LLM rosters in the registry", all(w not in reg.replace("# ADR-632: the three LLM tool ROSTERS (CHAT_PRIMITIVES / HEADLESS_PRIMITIVES /\n# FREDDIE_PRIMITIVES)", "") for w in ("CHAT_PRIMITIVES = [", "HEADLESS_PRIMITIVES = [", "FREDDIE_PRIMITIVES = [", "def get_tools_for_mode")))
from services.primitives.registry import HANDLERS, PRIMITIVES  # noqa: E402
_check("PRIMITIVES is derived and every tool has a handler", all(t["name"] in HANDLERS for t in PRIMITIVES) and len(PRIMITIVES) > 20)
_check("shared symbols live in system_calls", all(w in _read("api/services/system_calls.py") for w in ("def strip_provider(", "def accept_model_override(")))

print("§5 the two live frames are ratcheted (DP22 — the steward's ceilings retire with it)")
from services.lane_runner import _CONVENTIONS_FRAME  # noqa: E402
from services.authoring import _POSTURE_FRAME  # noqa: E402
scaffold = re.sub(r"\{[a-z_]+\}", "", _CONVENTIONS_FRAME)
posture = re.sub(r"\{[a-z_]+\}", "", _POSTURE_FRAME)
CONVENTIONS_SCAFFOLD_CEILING = 900      # measured 666 at ship (2026-09-02)
STUDIO_POSTURE_FRAME_CEILING = 11_000   # measured 10,566 at ship (2026-09-02)
_check(f"conventions scaffold under ceiling ({len(scaffold)} <= {CONVENTIONS_SCAFFOLD_CEILING})", len(scaffold) <= CONVENTIONS_SCAFFOLD_CEILING,
       "Raise only for a repeated observed failure, named in the raising commit (ADR-306 / DP22).")
_check(f"studio posture frame under ceiling ({len(posture)} <= {STUDIO_POSTURE_FRAME_CEILING})", len(posture) <= STUDIO_POSTURE_FRAME_CEILING,
       "Craft prose belongs in a skill (ADR-630), grammar stays derived; raise only with a receipt.")

print("§6 the web has no steward chrome")
for rel in ("web/contexts/NarrativeContext.tsx", "web/components/tp", "web/components/freddie", "web/components/shell/chrome/ChatDrawer.tsx",
            "web/components/shell/chrome/ChatDrawerSurface.tsx", "web/lib/freddie-persona.ts", "web/lib/steward-chrome.ts",
            "web/lib/realtime/use-session-messages-realtime.ts", "web/app/(authenticated)/system-agent", "web/app/(authenticated)/autonomy",
            "web/app/(authenticated)/expected-output", "web/app/(authenticated)/delegation", "web/hooks/useCommands.ts"):
    _check(f"{rel} deleted", not _exists(rel))
_check("the lane stream helper stays", _exists("web/lib/sse.ts"))
_check("the queue card lives with the queue", _exists("web/components/queue/ProposalCard.tsx"))
_check("shell context carries no drawer", "drawerOpen" not in _read("web/components/shell/ShellChromeContext.tsx"))
_check("chrome registry has no chat-drawer", "chat-drawer" not in _read("web/components/shell/ChromeRegistry.tsx"))
_check("client has no feed/commands calls", all(w not in _read("web/lib/api/client.ts") for w in ("/api/feed", "/api/commands", "queue_depth")))

print("§7 canon")
gl = _read("docs/architecture/GLOSSARY.md")
_check("GLOSSARY: Steward is historical", "**Steward** *(historical" in gl)
cm = _read("CLAUDE.md")
_check("CLAUDE.md protocol names live files", "api/services/lane_runner.py" in cm and "freddie_agent.py (the system-authored prompt layer)" not in cm)
_check("CLAUDE.md names this gate", "test_adr632_the_seat_retires.py" in cm)
_check("seat canon archived", _exists("docs/architecture/previous_versions/reviewer-seat-substrate.md") and not _exists("docs/architecture/reviewer-seat-substrate.md"))

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
