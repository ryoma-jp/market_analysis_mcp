from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.config import AppConfig, ExcerptConfig, HttpConfig, PathsConfig
from src.server import (
    SourceRecord,
    extract_evidence_quotes,
    extract_main_text,
    fetch_url,
    save_report,
    save_sources,
)


class _FakeResponse:
    def __init__(self, url: str, text: str, status_code: int = 200):
        self.url = url
        self.text = text
        self.status_code = status_code
        self.headers = {"content-type": "text/html; charset=utf-8"}
        self.content = text.encode("utf-8")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")


def test_fetch_url_allowlist_blocks() -> None:
    cfg = AppConfig(
        http=HttpConfig(allow_domains=["example.com"], timeout_seconds=1),
        paths=PathsConfig(),
        excerpts=ExcerptConfig(),
    )

    with pytest.raises(ValueError, match="Domain not allowed"):
        fetch_url("https://not-example.invalid/page", cfg)


def test_fetch_url_returns_fields() -> None:
    cfg = AppConfig(
        http=HttpConfig(allow_domains=["example.com"], timeout_seconds=1),
        paths=PathsConfig(),
        excerpts=ExcerptConfig(),
    )

    def fake_get(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse(
            url="https://example.com/final", text="<html>ok</html>"
        )

    with patch("requests.get", new=fake_get):
        r = fetch_url("https://example.com/start", cfg)

    assert str(r.final_url) == "https://example.com/final"
    assert r.status_code == 200
    assert isinstance(r.fetched_at, datetime)
    assert r.fetched_at.tzinfo is not None
    assert r.content_type
    assert "ok" in r.html


def test_fetch_url_max_content_length_enforced() -> None:
    cfg = AppConfig(
        http=HttpConfig(allow_domains=["example.com"], max_content_length=3),
        paths=PathsConfig(),
        excerpts=ExcerptConfig(),
    )

    def fake_get(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse(url="https://example.com/final", text="1234")

    with patch("requests.get", new=fake_get):
        with pytest.raises(ValueError, match="Content too large"):
            fetch_url("https://example.com/start", cfg)


def test_extract_main_text_basic() -> None:
    html = """
    <html>
      <head>
        <title>My Title</title>
        <meta property="og:site_name" content="MySite" />
      </head>
      <body>
        <article>
          <h1>My Title</h1>
          <p>Hello world</p>
        </article>
      </body>
    </html>
    """
    r = extract_main_text(html, base_url="https://example.com/x")
    assert r.title
    assert "Hello world" in r.main_text
    assert r.publisher in ("MySite", "example.com")


def test_extract_evidence_quotes_enforces_max_chars_and_position() -> None:
    text = "A" * 1000
    claims = ["AAA", "notfound"]
    out = extract_evidence_quotes(
        text, claims, max_chars=500, default_position="unknown"
    )

    assert len(out) == 2
    assert all(len(o.excerpt) <= 500 for o in out)

    assert out[0].position.startswith("chars ")
    assert out[1].position == "unknown"


def test_save_sources_and_report(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    records = [
        SourceRecord(
            url="https://example.com/a",
            final_url="https://example.com/a",
            fetched_at=now,
            title="t",
            publisher="example.com",
            published_date=None,
            category=None,
            confidence="high",
        )
    ]

    sources_path = tmp_path / "sources.json"
    report_path = tmp_path / "report.md"

    p1 = save_sources(records, str(sources_path))
    p2 = save_report("# hello", str(report_path))

    assert Path(p1).exists()
    assert Path(p2).exists()

    payload = json.loads(Path(p1).read_text(encoding="utf-8"))
    assert payload[0]["url"] == "https://example.com/a"
    assert "fetched_at" in payload[0]
    assert Path(p2).read_text(encoding="utf-8").startswith("#")
