"""
Minimal MCP-oriented tool implementations (fetch, extract, save
sources/report). MCP wiring (stdio server, tool schemas) should be added where
the platform expects.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl
from readability import Document

from .config import AppConfig, load_config

logger = logging.getLogger(__name__)


class FetchResult(BaseModel):
    final_url: HttpUrl
    status_code: int
    fetched_at: datetime
    content_type: Optional[str] = None
    html: str


class ExtractResult(BaseModel):
    title: Optional[str] = None
    main_text: str
    published_date: Optional[str] = None
    publisher: Optional[str] = None


class SourceRecord(BaseModel):
    url: HttpUrl
    final_url: Optional[HttpUrl] = None
    fetched_at: datetime
    title: Optional[str] = None
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    category: Optional[str] = None
    confidence: Optional[str] = None


def _check_allowlist(url: str, allow_domains: Optional[List[str]]) -> None:
    if not allow_domains:
        return
    host = urlparse(url).hostname or ""
    if not any(host.endswith(d) for d in allow_domains):
        raise ValueError(f"Domain not allowed by allowlist: {host}")


def fetch_url(url: str, cfg: Optional[AppConfig] = None) -> FetchResult:
    cfg = cfg or load_config()
    _check_allowlist(url, cfg.http.allow_domains)

    headers = {"User-Agent": cfg.http.user_agent}
    resp = requests.get(
        url,
        headers=headers,
        timeout=cfg.http.timeout_seconds,
        allow_redirects=True,
    )
    if cfg.http.max_content_length and (
        len(resp.content) > cfg.http.max_content_length
    ):
        raise ValueError("Content too large; aborted")
    resp.raise_for_status()
    fetched_at = datetime.now(timezone.utc)
    return FetchResult(
        final_url=resp.url,
        status_code=resp.status_code,
        fetched_at=fetched_at,
        content_type=resp.headers.get("content-type"),
        html=resp.text,
    )


def _extract_published_date(soup: BeautifulSoup) -> Optional[str]:
    meta_names = [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "pubdate"}),
        ("meta", {"name": "date"}),
        ("meta", {"itemprop": "datePublished"}),
        ("time", {"itemprop": "datePublished"}),
    ]
    for tag_name, attrs in meta_names:
        tag = soup.find(tag_name, attrs=attrs)
        if tag:
            content = tag.get("content") or tag.get_text(strip=True)
            if content:
                return content
    return None


def _extract_publisher(
    soup: BeautifulSoup, base_url: Optional[str]
) -> Optional[str]:
    meta = soup.find("meta", attrs={"property": "og:site_name"})
    if meta and meta.get("content"):
        return meta["content"]
    if base_url:
        try:
            from urllib.parse import urlparse

            return urlparse(base_url).hostname
        except Exception:  # pragma: no cover - defensive
            return None
    return None


def extract_main_text(
    html: str, base_url: Optional[str] = None
) -> ExtractResult:
    doc = Document(html)
    main_html = doc.summary(html_partial=True)
    title = doc.short_title()

    soup = BeautifulSoup(main_html, "lxml")
    text = soup.get_text("\n", strip=True)
    published_date = _extract_published_date(soup)
    publisher = _extract_publisher(soup, base_url)

    return ExtractResult(
        title=title or None,
        main_text=text,
        published_date=published_date,
        publisher=publisher,
    )


class EvidenceExcerpt(BaseModel):
    claim: str
    excerpt: str
    position: str


def extract_evidence_quotes(
    text: str,
    claims: List[str],
    max_chars: int = 500,
    default_position: str = "unknown",
) -> List[EvidenceExcerpt]:
    """Heuristic excerpt picker: find claim substring or take leading snippet.
    Enforces max_chars (agent_spec: 500 chars max per excerpt).
    """

    excerpts: List[EvidenceExcerpt] = []
    for claim in claims:
        lower_text = text.lower()
        lower_claim = claim.lower()
        idx = lower_text.find(lower_claim) if lower_claim else -1
        if idx >= 0:
            start = max(0, idx - 120)
            end = min(len(text), idx + len(claim) + 120)
            snippet = text[start:end]
            position = f"chars {start}-{end}"
        else:
            snippet = text[: max_chars]
            position = default_position

        if len(snippet) > max_chars:
            snippet = snippet[: max_chars]

        excerpts.append(
            EvidenceExcerpt(
                claim=claim,
                excerpt=snippet,
                position=position,
            )
        )
    return excerpts


def save_sources(records: List[SourceRecord], output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.model_dump(mode="json") for r in records]
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return str(path)


def save_report(markdown_text: str, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown_text, encoding="utf-8")
    return str(path)


# TODO: Wire these functions into an MCP server (stdio) with tool schemas
# - fetch_url
# - extract_main_text
# - save_sources
# - save_report
# Optional future tool: extract_evidence_quotes (enforce 500-char excerpt)


if __name__ == "__main__":
    # Placeholder for manual testing; actual MCP entrypoint will differ
    logging.basicConfig(level=logging.INFO)
    print(
        "This module provides tool functions. Integrate with your MCP server "
        "runner."
    )
