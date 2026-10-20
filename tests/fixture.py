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
    "rtm": "docs/rtm.md",
    "layers": [
        {"id": "br", "label": "BR", "prefixes": ["BR"],
         "define": [{"files": ["docs/brd.md"], "how": "table"}],
         "attrs": [{"name": "source", "file": "docs/rtm.md", "key_col": "BR", "value_col": "Source"}],
         "require": [["@source"]], "severity": "P2"},
        {"id": "req", "label": "FR", "prefixes": ["FR"],
         "define": [{"files": ["docs/frd.md"], "how": "heading"}],
         "upstream": ["br"], "require": [["br"]], "severity": "P1"},
        {"id": "story", "label": "Story", "prefixes": ["STORY"],
         "define": [{"files": ["docs/stories.md"], "how": "heading"}],
         "upstream": ["req"], "require": [["req"]], "severity": "P1",
         "children": {"id": "ac", "label": "AC", "suffix": "AC",
                      "pattern": "^\\s*[-*]\\s*\\*\\*AC(\\d+)\\b"}},
        {"id": "hld", "label": "HLD", "prefixes": ["CMP"],
         "define": [{"files": ["docs/hld.md"], "how": "table"}],
         "upstream": ["req"], "require": [["req"]], "severity": "P2"},
        {"id": "lld", "label": "LLD", "prefixes": ["TASK"],
         "define": [{"files": ["docs/lld.md"], "how": "table"}],
         "upstream": ["hld", "req"], "trace_via": ["req"],
         "require": [["hld"], ["req"]], "severity": "P1"},
        {"id": "code", "label": "Code", "kind": "files", "files": ["src/main/**/*.java"],
         "upstream": ["lld"], "require": [["lld"]], "severity": "P2"},
        {"id": "test", "label": "Test", "kind": "files", "files": ["src/test/**/*.java"],
         "upstream": ["ac", "br"], "require": [["ac", "br"]], "severity": "P1",
         "ref_marker": "Verifies:"},
    ],
    "coverage": [{"from": "br", "to": "test", "severity": "P3"}],
    "render": {
        "stages": {"req": "Specified", "hld": "In Design", "lld": "Designed",
                   "code": "Implemented", "test": "Tested"},
        "blocks": [
            {"id": "forward", "type": "forward", "root": "br",
             "columns": ["req", "hld", "lld", "code", "test"]},
            {"id": "justify", "type": "justify", "layer": "lld"},
            {"id": "ac", "type": "children", "parent": "story", "target": "test"},
            {"id": "backward", "type": "backward", "layer": "test", "up": ["br"]},
            {"id": "summary", "type": "summary"},
        ],
    },
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
