from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class HttpConfig:
    user_agent: str = "market-analysis-mcp/0.1"
    timeout_seconds: int = 10
    max_content_length: int = 5_000_000
    allow_domains: Optional[List[str]] = None


@dataclass
class PathsConfig:
    reports_dir: str = "reports"
    sources_dir: str = "sources"


@dataclass
class ExcerptConfig:
    max_chars: int = 500
    default_position: str = "unknown"


@dataclass
class AppConfig:
    http: HttpConfig = field(default_factory=HttpConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    excerpts: ExcerptConfig = field(default_factory=ExcerptConfig)


def load_config(path: Optional[str] = None) -> AppConfig:
    """Load config from YAML; falls back to defaults if missing."""
    cfg_path = (
        Path(path)
        if path
        else Path(os.getenv("APP_CONFIG", "env/config.yaml"))
    )
    if not cfg_path.exists():
        return AppConfig()
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    http = data.get("http", {})
    paths = data.get("paths", {})
    excerpts = data.get("excerpts", {})
    return AppConfig(
        http=HttpConfig(**http),
        paths=PathsConfig(**paths),
        excerpts=ExcerptConfig(**excerpts),
    )
