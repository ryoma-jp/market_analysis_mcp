"""MCP stdio server entrypoint.

This module exposes the existing tool functions in `src/server.py` as MCP tools
using the official MCP Python SDK.

Run (stdio):
    python -m src.mcp_server

Note: `src/main.py` remains as a legacy development NDJSON protocol.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .server import (
    SourceRecord,
    extract_evidence_quotes as _extract_evidence_quotes,
    extract_main_text as _extract_main_text,
    fetch_url as _fetch_url,
    save_report as _save_report,
    save_sources as _save_sources,
)

mcp = FastMCP(
    "market-analysis-mcp",
    json_response=True,
    instructions=(
        "Tools for market/industry analysis: fetch URL HTML, extract main text, "
        "extract short evidence excerpts (<=500 chars), and save sources/reports."
    ),
)


@mcp.tool()
def fetch_url(url: str) -> dict[str, Any]:
    """Fetch a URL and return HTML and metadata."""
    cfg = load_config()
    return _fetch_url(url, cfg).model_dump(mode="json")


@mcp.tool()
def extract_main_text(html: str, base_url: str | None = None) -> dict[str, Any]:
    """Extract main text and basic metadata from HTML."""
    return _extract_main_text(html, base_url).model_dump(mode="json")


@mcp.tool()
def extract_evidence_quotes(
    text: str,
    claims: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return short excerpts (max 500 chars by default) per claim."""
    cfg = load_config()
    out = _extract_evidence_quotes(
        text,
        claims or [],
        max_chars=cfg.excerpts.max_chars,
        default_position=cfg.excerpts.default_position,
    )
    return [r.model_dump(mode="json") for r in out]


@mcp.tool()
def save_sources(records: list[dict[str, Any]], output_path: str) -> dict[str, str]:
    """Save source records to JSON."""
    parsed = [SourceRecord(**r) for r in records]
    return {"path": _save_sources(parsed, output_path)}


@mcp.tool()
def save_report(markdown_text: str, output_path: str) -> dict[str, str]:
    """Save a markdown report."""
    return {"path": _save_report(markdown_text, output_path)}


def main() -> None:
    # Default transport for FastMCP is stdio.
    mcp.run()


if __name__ == "__main__":
    main()
