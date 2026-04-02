import asyncio

from integrations.core.types import ExportStatus
from services import delivery


def test_build_email_assets_from_manifest_uses_manifest_urls():
    manifest = {
        "files": [
            {"path": "output.md", "type": "text/markdown", "role": "primary"},
            {
                "path": "charts/growth-chart.svg",
                "type": "image/svg+xml",
                "role": "rendered",
                "content_url": "https://cdn.example.com/growth-chart.svg",
            },
        ]
    }

    assets = delivery._build_email_assets_from_manifest(manifest)

    assert {"ref": "charts/growth-chart.svg", "url": "https://cdn.example.com/growth-chart.svg"} in assets
    assert {"ref": "growth-chart.svg", "url": "https://cdn.example.com/growth-chart.svg"} in assets


def test_deliver_email_reuses_composed_html_when_email_compose_fails(monkeypatch):
    captured = {}

    async def fake_compose_email_html(markdown, title, assets=None):
        return None

    async def fake_send_email(**kwargs):
        captured.update(kwargs)

        class Result:
            success = True
            message_id = "msg_123"
            error = None

        return Result()

    monkeypatch.setattr(delivery, "_compose_email_html", fake_compose_email_html)
    monkeypatch.setattr("jobs.email.send_email", fake_send_email)

    result = asyncio.run(
        delivery._deliver_email_from_manifest(
            destination={"platform": "email", "target": "test@example.com"},
            text_content="# Market Context Bootstrap Summary",
            manifest={"files": []},
            title="Market Research",
            version_number=1,
            role="researcher",
            agent_id="agent-123",
            mode=None,
            composed_html=(
                "<html><body><h1>Rendered output</h1>"
                "<script>window.bad = true</script>"
                "<iframe src=\"https://example.com/embed\"></iframe>"
                "</body></html>"
            ),
            task_slug="market-research",
        )
    )

    assert result.status == ExportStatus.SUCCESS
    assert "<h1>Rendered output</h1>" in captured["html"]
    assert "window.bad" not in captured["html"]
    assert "Open embedded content" in captured["html"]
    assert "# Market Context Bootstrap Summary" not in captured["html"]


def test_deliver_email_passes_manifest_assets_into_compose(monkeypatch):
    captured = {}

    async def fake_compose_email_html(markdown, title, assets=None):
        captured["markdown"] = markdown
        captured["title"] = title
        captured["assets"] = assets or []
        return "<html><body><p>ok</p></body></html>"

    async def fake_send_email(**kwargs):
        captured["html"] = kwargs["html"]

        class Result:
            success = True
            message_id = "msg_456"
            error = None

        return Result()

    monkeypatch.setattr(delivery, "_compose_email_html", fake_compose_email_html)
    monkeypatch.setattr("jobs.email.send_email", fake_send_email)

    result = asyncio.run(
        delivery._deliver_email_from_manifest(
            destination={"platform": "email", "target": "test@example.com"},
            text_content="![Growth](charts/growth-chart.svg)",
            manifest={
                "files": [
                    {
                        "path": "charts/growth-chart.svg",
                        "type": "image/svg+xml",
                        "role": "rendered",
                        "content_url": "https://cdn.example.com/growth-chart.svg",
                    }
                ]
            },
            title="Market Research",
            version_number=1,
            role="researcher",
            agent_id="agent-123",
            mode=None,
            composed_html=None,
            task_slug="market-research",
        )
    )

    assert result.status == ExportStatus.SUCCESS
    assert {"ref": "charts/growth-chart.svg", "url": "https://cdn.example.com/growth-chart.svg"} in captured["assets"]
    assert {"ref": "growth-chart.svg", "url": "https://cdn.example.com/growth-chart.svg"} in captured["assets"]
