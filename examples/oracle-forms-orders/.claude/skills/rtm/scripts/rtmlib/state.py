"""Hook state under <root>/.rtm/ (add `.rtm/*` except baseline.json to .gitignore).

  baseline.json  accepted findings (committed; written by `rtm baseline`)
  last.json      fingerprints after the most recent sync
  start.json     fingerprints before the first edit of the current Claude turn(s)
  dirty          watched files touched since the last clean Stop
"""
from __future__ import annotations

import json
from pathlib import Path


def _dir(root: Path) -> Path:
    d = root / ".rtm"
    d.mkdir(exist_ok=True)
    return d


def read_set(root: Path, name: str) -> set[str] | None:
    try:
        data = json.loads((root / ".rtm" / name).read_text())
        return set(data["fingerprints"])
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return None


def write_set(root: Path, name: str, fps) -> None:
    (_dir(root) / name).write_text(json.dumps({"fingerprints": sorted(fps)}, indent=1) + "\n")


def dirty(root: Path) -> list[str]:
    try:
        return [l for l in (root / ".rtm" / "dirty").read_text().splitlines() if l]
    except FileNotFoundError:
        return []


def mark_dirty(root: Path, rel: str) -> bool:
    """Record rel; returns True if this is the first dirty file (a new 'session')."""
    cur = dirty(root)
    if rel not in cur:
        (_dir(root) / "dirty").write_text("\n".join(cur + [rel]) + "\n")
    return not cur


def clear(root: Path) -> None:
    for name in ("dirty", "start.json"):
        (root / ".rtm" / name).unlink(missing_ok=True)
