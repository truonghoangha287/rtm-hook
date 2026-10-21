"""A tiny repo exercising every layer type. `make(tmp)` writes it and returns the root."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "rtm" / "scripts"
sys.path.insert(0, str(SCRIPTS))

FILES = {
    "docs/brd.md": """# BRD
| ID | Business requirement | Priority |
|---|---|---|
| BR-001 | Send payments | MUST |
| BR-002 | Screen payments | MUST |
""",
    "docs/frd.md": """# FRD
### FR-001 — Send API *(traces: BR-001)*
Body text.
### FR-002 — Screening *(traces: BR-002)*
""",
    "docs/stories.md": """# Stories
## STORY-001 — Send money
| Field | Value |
|---|---|
| Traces | FR-001 |

- **AC1 (happy):** *Given* ok *then* sent.
- **AC2 (negative):** *Given* bad *then* rejected.
""",
    "docs/hld.md": """# HLD
| ID | Component | Traces |
|---|---|---|
| CMP-001 | Gateway | FR-001 |
| CMP-002 | Screener | FR-002 |
""",
    "docs/lld.md": """# LLD
| ID | Task | Traces |
|---|---|---|
| TASK-001 | Build gateway | FR-001 · CMP-001 |
| TASK-002 ⟐ | Build screener | FR-002 · CMP-002 |
""",
    "src/main/Gateway.java": "/** Gateway (TASK-001). */\nclass Gateway {}\n",
    "src/main/Screener.java": "/** Screener (TASK-002). */\nclass Screener {}\n",
    "src/test/GatewayTest.java": "/**\n * Verifies: STORY-001/AC1\n */\nclass GatewayTest {}\n",
    "docs/rtm.md": """# RTM

## 1. Source → BR (hand-maintained)

| BR | Source | Priority |
|---|---|---|
| BR-001 | Regulation X | MUST |
| BR-002 | Regulation Y | MUST |

## Notes

Hand-written notes stay put.
""",
}

CONFIG = {
    "schema": 2,
    "rtm": {"index": "docs/rtm.md"},
    "flow": [
        {"step": "br", "label": "BR", "severity": "P2",
         "produces": {"ids": ["BR"], "in": [{"files": ["docs/brd.md"], "how": "table"}]},
         "consumes": {"attrs": ["source"]},
         "attrs": {"source": {"from": "index", "key_col": "BR", "value_col": "Source"}}},
        {"step": "req", "label": "FR", "severity": "P1",
         "produces": {"ids": ["FR"], "in": [{"files": ["docs/frd.md"], "how": "heading"}]},
         "consumes": {"steps": ["br"]}},
        {"step": "story", "label": "Story", "severity": "P1",
         "produces": {"ids": ["STORY"], "in": [{"files": ["docs/stories.md"], "how": "heading"}],
                      "children": {"step": "ac", "label": "AC", "suffix": "AC",
                                   "pattern": "^\\s*[-*]\\s*\\*\\*AC(\\d+)\\b"}},
         "consumes": {"steps": ["req"]}},
        {"step": "hld", "label": "HLD", "severity": "P2",
         "produces": {"ids": ["CMP"], "in": [{"files": ["docs/hld.md"], "how": "table"}]},
         "consumes": {"steps": ["req"]}},
        {"step": "lld", "label": "LLD", "severity": "P1",
         "produces": {"ids": ["TASK"], "in": [{"files": ["docs/lld.md"], "how": "table"}]},
         "consumes": {"steps": ["hld", "req"], "rule": "all", "walk": ["req"]}},
        {"step": "code", "label": "Code", "severity": "P2",
         "produces": {"files": ["src/main/**/*.java"]}, "consumes": {"steps": ["lld"]}},
        {"step": "test", "label": "Test", "severity": "P1",
         "produces": {"files": ["src/test/**/*.java"]},
         "consumes": {"steps": ["ac", "br"], "rule": "any", "marker": "Verifies:"}},
    ],
    "coverage": [{"from": "br", "to": "test", "severity": "P3"}],
    "status": {"req": "Specified", "hld": "In Design", "lld": "Designed",
               "code": "Implemented", "test": "Tested"},
    "views": [
        {"id": "forward", "type": "forward", "root": "br", "columns": ["req", "hld", "lld", "code", "test"]},
        {"id": "justify", "type": "justify", "layer": "lld"},
        {"id": "ac", "type": "children", "parent": "story", "target": "test"},
        {"id": "backward", "type": "backward", "layer": "test", "up": ["br"]},
        {"id": "summary", "type": "summary"},
    ],
}


def make(tmp: Path) -> Path:
    for rel, text in FILES.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (tmp / "rtm.config.json").write_text(json.dumps(CONFIG, indent=1))
    return tmp


def cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "rtm.py"), "--root", str(root), *args],
                          capture_output=True, text=True)


def hook(root: Path, mode: str, payload: dict) -> dict | None:
    payload = {"cwd": str(root), **payload}
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)}
    r = subprocess.run([sys.executable, str(SCRIPTS / "rtm_hook.py"), mode],
                       input=json.dumps(payload), capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


def edit(root: Path, rel: str, old: str, new: str) -> dict:
    """Apply an Edit to disk and return the matching tool_input."""
    p = root / rel
    p.write_text(p.read_text().replace(old, new, 1))
    return {"tool_name": "Edit",
            "tool_input": {"file_path": str(p), "old_string": old, "new_string": new}}


__all__ = ["make", "cli", "hook", "edit", "shutil"]
