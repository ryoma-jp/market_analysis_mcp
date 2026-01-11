from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_stdio_list_tools() -> None:
    env = os.environ.copy()
    repo_root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(repo_root)

    proc = subprocess.run(
        [sys.executable, "-m", "src.main"],
        input=json.dumps({"action": "list_tools"}) + "\n",
        text=True,
        capture_output=True,
        env=env,
        cwd=repo_root,
        check=True,
    )

    line = proc.stdout.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["ok"] is True
    assert "tools" in payload["result"]
    assert "fetch_url" in payload["result"]["tools"]
