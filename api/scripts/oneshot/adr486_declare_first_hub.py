"""ADR-486 R0 Hat-B eval — declare the first radar hub in prod.

Writes /workspace/operation/ai-frontier/_radar.yaml for the operator's
workspace through write_revision (the one door), authored as operator
(the operator delegated this session's implementation run, 2026-07-24).

fire_on_activation: true → the hub sweeps on the first scheduler tick after
the R0 deploy; thereafter daily 21:00 UTC (~06:00 KST).

Run:  cd api && python3 scripts/oneshot/adr486_declare_first_hub.py --apply
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"  # kvkthecreator@gmail.com
PATH = "/workspace/operation/ai-frontier/_radar.yaml"

DECLARATION = """\
# _radar.yaml — AI Radar hub declaration (ADR-486)
# The hub: what the frontier of AI shipped that matters for building yarnnn.
schedule: "0 21 * * *"   # daily 21:00 UTC (~06:00 KST)
fire_on_activation: true
paused: false
prompt: |
  Track frontier AI: model releases, agent tooling, LLM platform shifts, and
  anything bearing on agent-native operating systems, durable AI memory, or
  multi-agent workspaces. Skip general tech news, funding gossip, and culture
  pieces — this radar exists to catch capability and platform moves yarnnn
  should react to.
sources:
  - id: hn-front
    url: https://news.ycombinator.com/rss
    max_entries: 12
  - id: simonwillison
    url: https://simonwillison.net/atom/everything/
    max_entries: 8
"""


def main() -> None:
    apply = "--apply" in sys.argv
    from supabase import create_client
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    existing = (
        client.table("workspace_files").select("path")
        .eq("user_id", USER_ID).eq("path", PATH).limit(1).execute()
    ).data or []
    print(f"existing declaration: {'YES' if existing else 'no'}")

    # Sanity: the declaration parses into a schedulable hub before it lands.
    from services.radar import parse_radar_yaml, topic_from_declaration_path
    topic = topic_from_declaration_path(PATH)
    hub = parse_radar_yaml(DECLARATION, topic=topic, declaration_path=PATH, user_id=USER_ID)
    assert hub and hub.slug == "radar:ai-frontier" and hub.schedule == "0 21 * * *", hub
    assert hub.options.get("fire_on_activation") is True
    print(f"parsed OK: slug={hub.slug} schedule={hub.schedule} fire_on_activation=True")

    if not apply:
        print("dry-run — pass --apply to write")
        return

    from services.authored_substrate import write_revision
    rev = write_revision(
        client,
        user_id=USER_ID,
        path=PATH,
        content=DECLARATION,
        authored_by="operator",
        message="declare the first radar hub (ADR-486 R0 Hat-B eval; "
                "implementation run delegated 2026-07-24)",
    )
    print(f"written: {PATH} (revision {rev})")


if __name__ == "__main__":
    main()
