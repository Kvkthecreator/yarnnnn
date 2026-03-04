#!/usr/bin/env python3
"""Auto-sync GitBook changelog + versioning metadata from git history."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
GITBOOK_DIR = REPO_ROOT / "docs" / "gitbook"
CHANGELOG_PATH = GITBOOK_DIR / "changelog.md"
VERSIONING_PATH = GITBOOK_DIR / "resources" / "versioning.md"
STATE_PATH = GITBOOK_DIR / ".sync-state.json"

CHANGELOG_START = "<!-- AUTO_SYNC_START -->"
CHANGELOG_END = "<!-- AUTO_SYNC_END -->"
VERSIONING_START = "<!-- GITBOOK_VERSIONING_START -->"
VERSIONING_END = "<!-- GITBOOK_VERSIONING_END -->"


@dataclass
class Commit:
    sha: str
    date: str
    subject: str
    files: list[str]


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def safe_run_git(args: list[str]) -> str:
    try:
        return run_git(args)
    except Exception:
        return ""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"history": []}
    try:
        data = json.loads(read_text(STATE_PATH))
        if not isinstance(data, dict):
            return {"history": []}
        data.setdefault("history", [])
        return data
    except Exception:
        return {"history": []}


def write_state(state: dict[str, Any]) -> None:
    write_text(STATE_PATH, json.dumps(state, indent=2, sort_keys=True) + "\n")


def commit_exists(sha: str | None) -> bool:
    if not sha:
        return False
    return subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def get_api_version() -> str:
    text = read_text(REPO_ROOT / "api" / "main.py")
    match = re.search(r'version\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else "unknown"


def get_web_version() -> str:
    pkg = json.loads(read_text(REPO_ROOT / "web" / "package.json"))
    version = pkg.get("version")
    return str(version) if version else "unknown"


def build_docs_version(api_version: str, web_version: str, now: datetime) -> str:
    stamp = now.strftime("%Y%m%d")
    if api_version == web_version:
        return f"v{api_version}-docs.{stamp}"
    web = web_version.replace(".", "_")
    return f"v{api_version}-docs.{stamp}-web{web}"


def is_relevant(files: list[str]) -> bool:
    for path in files:
        if path.startswith("docs/"):
            return True
        if path.startswith("content/posts/"):
            return True
        if path.startswith("api/routes/"):
            return True
        if path in {
            "api/main.py",
            "api/services/platform_limits.py",
            "web/package.json",
            "web/types/index.ts",
            "web/app/pricing/page.tsx",
        }:
            return True
    return False


def parse_git_log(raw: str) -> list[Commit]:
    commits: list[Commit] = []
    current: Commit | None = None
    expect_meta = False

    for line in raw.splitlines():
        if line == "__COMMIT__":
            if current is not None:
                commits.append(current)
            current = None
            expect_meta = True
            continue

        if expect_meta:
            expect_meta = False
            parts = line.split("\x1f")
            if len(parts) != 3:
                continue
            sha, date, subject = parts
            current = Commit(sha=sha, date=date, subject=subject, files=[])
            continue

        if current is None:
            continue

        stripped = line.strip()
        if not stripped:
            continue
        current.files.append(stripped)

    if current is not None:
        commits.append(current)

    return commits


def collect_commits(last_synced_commit: str | None) -> tuple[list[Commit], str]:
    log_args = [
        "log",
        "--date=short",
        "--pretty=format:__COMMIT__%n%H%x1f%ad%x1f%s",
        "--name-only",
    ]

    range_label = "recent"
    if commit_exists(last_synced_commit):
        head = run_git(["rev-parse", "HEAD"])[:7]
        base = last_synced_commit[:7]
        log_args.append(f"{last_synced_commit}..HEAD")
        range_label = f"{base}..{head}"
    else:
        log_args.extend(["-n", "30"])

    log_args.extend(["--", "api", "docs", "web", "content"])
    raw = safe_run_git(log_args)
    all_commits = parse_git_log(raw)
    filtered = [c for c in all_commits if is_relevant(c.files)]

    if filtered and range_label == "recent":
        oldest = filtered[-1].sha[:7]
        newest = filtered[0].sha[:7]
        range_label = f"{oldest}..{newest}"

    return filtered, range_label


def collect_recent_commits(limit: int = 20) -> tuple[list[Commit], str]:
    raw = safe_run_git(
        [
            "log",
            "--date=short",
            "--pretty=format:__COMMIT__%n%H%x1f%ad%x1f%s",
            "--name-only",
            "-n",
            str(limit),
            "--",
            "api",
            "docs",
            "web",
            "content",
        ]
    )
    commits = [c for c in parse_git_log(raw) if is_relevant(c.files)]
    if not commits:
        return [], "recent"
    return commits, f"{commits[-1].sha[:7]}..{commits[0].sha[:7]}"


def replace_marker_block(text: str, start: str, end: str, body: str) -> str:
    start_idx = text.find(start)
    end_idx = text.find(end)

    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        if not text.endswith("\n"):
            text += "\n"
        return f"{text}\n{start}\n{body}\n{end}\n"

    prefix = text[: start_idx + len(start)]
    suffix = text[end_idx:]
    return f"{prefix}\n{body}\n{suffix}"


def build_changelog_auto_block(
    now: datetime,
    docs_version: str,
    head: str,
    range_label: str,
    new_commits_count: int,
    displayed_commits: list[Commit],
) -> str:
    lines = [
        "## Auto-synced updates",
        "",
        f"- Last synced: `{now.strftime('%Y-%m-%d %H:%M:%SZ')}`",
        f"- Docs version: `{docs_version}`",
        f"- Source commit: `{head[:7]}`",
        f"- Source range: `{range_label}`",
        f"- New commits since last sync: `{new_commits_count}`",
        f"- Displayed commits: `{len(displayed_commits)}`",
        "",
        "### Recent commits",
    ]

    if not displayed_commits:
        lines.append("- No relevant commits found since last sync.")
        return "\n".join(lines)

    for commit in displayed_commits[:20]:
        lines.append(f"- {commit.date} `{commit.sha[:7]}` {commit.subject}")

    return "\n".join(lines)


def build_versioning_block(
    now: datetime,
    docs_version: str,
    api_version: str,
    web_version: str,
    head: str,
    range_label: str,
    new_commits_count: int,
    history: list[dict[str, Any]],
) -> str:
    lines = [
        "## Current snapshot",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Last synced (UTC) | `{now.strftime('%Y-%m-%d %H:%M:%SZ')}` |",
        f"| Docs version | `{docs_version}` |",
        f"| API version | `{api_version}` |",
        f"| Web version | `{web_version}` |",
        f"| Source commit | `{head[:7]}` |",
        f"| Source range | `{range_label}` |",
        f"| New commits since last sync | `{new_commits_count}` |",
        "",
        "## Recent sync history",
        "",
        "| Synced at (UTC) | Docs version | Commit | Range | Commits |",
        "|---|---|---|---|---|",
    ]

    if history:
        for item in reversed(history[-10:]):
            lines.append(
                "| `{synced_at}` | `{docs_version}` | `{head}` | `{range}` | `{count}` |".format(
                    synced_at=item.get("synced_at", "?"),
                    docs_version=item.get("docs_version", "?"),
                    head=str(item.get("head", "?"))[:7],
                    range=item.get("range", "?"),
                    count=item.get("commit_count", 0),
                )
            )
    else:
        lines.append("| - | - | - | - | - |")

    return "\n".join(lines)


def main() -> None:
    now = datetime.now(timezone.utc)
    head = run_git(["rev-parse", "HEAD"])
    api_version = get_api_version()
    web_version = get_web_version()
    docs_version = build_docs_version(api_version, web_version, now)

    state = read_state()
    last_synced_commit = state.get("last_synced_commit")

    new_commits, range_label = collect_commits(last_synced_commit)
    displayed_commits = new_commits
    if not displayed_commits:
        displayed_commits, fallback_range = collect_recent_commits(limit=20)
        if fallback_range != "recent":
            range_label = fallback_range

    changelog_text = read_text(CHANGELOG_PATH)
    changelog_block = build_changelog_auto_block(
        now=now,
        docs_version=docs_version,
        head=head,
        range_label=range_label,
        new_commits_count=len(new_commits),
        displayed_commits=displayed_commits,
    )
    changelog_text = replace_marker_block(changelog_text, CHANGELOG_START, CHANGELOG_END, changelog_block)
    write_text(CHANGELOG_PATH, changelog_text)

    history = state.get("history", [])
    if not history or history[-1].get("head") != head:
        history.append(
            {
                "synced_at": now.strftime("%Y-%m-%d %H:%M:%SZ"),
                "docs_version": docs_version,
                "head": head,
                "range": range_label,
                "commit_count": len(new_commits),
            }
        )

    versioning_text = read_text(VERSIONING_PATH)
    versioning_block = build_versioning_block(
        now=now,
        docs_version=docs_version,
        api_version=api_version,
        web_version=web_version,
        head=head,
        range_label=range_label,
        new_commits_count=len(new_commits),
        history=history,
    )
    versioning_text = replace_marker_block(versioning_text, VERSIONING_START, VERSIONING_END, versioning_block)
    write_text(VERSIONING_PATH, versioning_text)

    state.update(
        {
            "last_synced_at": now.strftime("%Y-%m-%d %H:%M:%SZ"),
            "last_synced_commit": head,
            "docs_version": docs_version,
            "history": history,
        }
    )
    write_state(state)

    print(f"Synced GitBook docs: {docs_version} ({head[:7]})")


if __name__ == "__main__":
    main()
