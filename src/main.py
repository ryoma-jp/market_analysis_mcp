"""Minimal NDJSON stdio server for MCP-style tool invocation.

Protocol (very small, for development use):
- Input: one JSON object per line.
  - {"action": "list_tools"}
  - {"action": "invoke", "tool": "fetch_url", "params": {...}}
- Output: one JSON object per line.
  - {"ok": true, "result": ...}
  - {"ok": false, "error": "message"}

This is intentionally minimal to keep dependencies small. Replace with your
preferred MCP framework as needed.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict

from .config import load_config
from .server import (
    SourceRecord,
    extract_evidence_quotes,
    extract_main_text,
    fetch_url,
    save_report,
    save_sources,
)


def _print(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _handle_invoke(tool: str, params: Dict[str, Any]) -> Any:
    cfg = load_config()
    if tool == "fetch_url":
        url = params.get("url")
        return fetch_url(url, cfg).model_dump()
    if tool == "extract_main_text":
        html = params.get("html")
        base_url = params.get("base_url")
        return extract_main_text(html, base_url).model_dump()
    if tool == "extract_evidence_quotes":
        text = params.get("text")
        claims = params.get("claims", [])
        max_chars = cfg.excerpts.max_chars
        position = cfg.excerpts.default_position
        result = extract_evidence_quotes(text, claims, max_chars, position)
        return [r.model_dump() for r in result]
    if tool == "save_sources":
        records_raw = params.get("records", [])
        output_path = params.get("output_path")
        records = [SourceRecord(**r) for r in records_raw]
        return {"path": save_sources(records, output_path)}
    if tool == "save_report":
        markdown_text = params.get("markdown_text")
        output_path = params.get("output_path")
        return {"path": save_report(markdown_text, output_path)}
    raise ValueError(f"Unknown tool: {tool}")


def main() -> None:
    tools = [
        "fetch_url",
        "extract_main_text",
        "extract_evidence_quotes",
        "save_sources",
        "save_report",
    ]

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            action = req.get("action")
            if action == "list_tools":
                _print({"ok": True, "result": {"tools": tools}})
                continue
            if action == "invoke":
                tool = req.get("tool")
                params = req.get("params", {})
                result = _handle_invoke(tool, params)
                _print({"ok": True, "result": result})
                continue
            _print({"ok": False, "error": "unknown action"})
        except Exception as exc:  # pragma: no cover - defensive in stdio loop
            _print({"ok": False, "error": str(exc)})


if __name__ == "__main__":
    main()
