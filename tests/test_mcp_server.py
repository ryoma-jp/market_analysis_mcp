from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.config import AppConfig, ExcerptConfig, HttpConfig, PathsConfig


class _FakeModel:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self, mode: str = "json"):
        assert mode == "json"
        return self._payload


def test_mcp_server_imports() -> None:
    # Import should succeed (valid MCP SDK API usage).
    import src.mcp_server  # noqa: F401


def test_extract_evidence_quotes_claims_none_returns_empty(monkeypatch) -> None:
    import src.mcp_server as m

    cfg = AppConfig(
        http=HttpConfig(),
        paths=PathsConfig(),
        excerpts=ExcerptConfig(max_chars=500, default_position="unknown"),
    )
    monkeypatch.setattr(m, "load_config", lambda: cfg)

    out = m.extract_evidence_quotes(text="hello", claims=None)
    assert out == []


def test_fetch_url_wrapper_uses_loaded_config(monkeypatch) -> None:
    import src.mcp_server as m

    cfg = AppConfig(
        http=HttpConfig(allow_domains=None),
        paths=PathsConfig(),
        excerpts=ExcerptConfig(max_chars=500, default_position="unknown"),
    )
    monkeypatch.setattr(m, "load_config", lambda: cfg)

    def fake_fetch_url(url: str, passed_cfg: AppConfig):
        assert url == "https://example.com"
        assert passed_cfg is cfg
        return _FakeModel(
            {
                "final_url": "https://example.com",
                "status_code": 200,
                "fetched_at": "2020-01-01T00:00:00+00:00",
                "content_type": "text/html",
                "html": "<html>ok</html>",
            }
        )

    monkeypatch.setattr(m, "_fetch_url", fake_fetch_url)

    out = m.fetch_url("https://example.com")
    assert out["status_code"] == 200
    assert "ok" in out["html"]


def test_mcp_wrappers_extract_and_save(tmp_path, monkeypatch) -> None:
    import src.mcp_server as m

    cfg = AppConfig(
        http=HttpConfig(),
        paths=PathsConfig(),
        excerpts=ExcerptConfig(max_chars=500, default_position="unknown"),
    )
    monkeypatch.setattr(m, "load_config", lambda: cfg)

    html = """
    <html>
      <head><title>Example</title><meta property='og:site_name' content='ExampleSite'></head>
      <body><article><h1>Hello</h1><p>This is the main content.</p></article></body>
    </html>
    """.strip()

    extracted = m.extract_main_text(html, base_url="https://example.com")
    assert isinstance(extracted, dict)
    assert "main_text" in extracted
    assert "This is the main content" in extracted["main_text"]

    quotes = m.extract_evidence_quotes(
        text=extracted["main_text"],
        claims=["main content"],
    )
    assert isinstance(quotes, list)
    assert len(quotes) == 1
    assert quotes[0]["claim"] == "main content"
    assert len(quotes[0]["excerpt"]) <= 500

    report_path = tmp_path / "reports" / "report.md"
    out_report = m.save_report("# Title\n\nBody", str(report_path))
    assert out_report["path"].endswith("report.md")
    assert report_path.read_text(encoding="utf-8") == "# Title\n\nBody"

    sources_path = tmp_path / "sources" / "sources.json"
    now = datetime.now(timezone.utc).isoformat()
    out_sources = m.save_sources(
        records=[
            {
                "url": "https://example.com",
                "fetched_at": now,
                "title": "Example",
                "publisher": "ExampleSite",
            }
        ],
        output_path=str(sources_path),
    )
    assert out_sources["path"].endswith("sources.json")
    assert sources_path.exists()


def test_save_sources_rejects_invalid_record(tmp_path) -> None:
    import src.mcp_server as m

    sources_path = tmp_path / "sources" / "sources.json"
    now = datetime.now(timezone.utc).isoformat()

    with pytest.raises(Exception):
        m.save_sources(
            records=[
                {
                    # missing required "url"
                    "fetched_at": now,
                    "title": "Example",
                }
            ],
            output_path=str(sources_path),
        )
