"""High-level operations shared by the CLI and the hooks."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from . import checks, render, state
from .checks import Finding
from .config import Config, load
from .graph import Graph


@dataclass
class Result:
    graph: Graph
    findings: list[Finding]
    changes: dict[str, tuple[int, int]] = field(default_factory=dict)  # block -> (+rows, -rows)
    discarded: list[str] = field(default_factory=list)  # hand-edited generated blocks overwritten
    removed: list[str] = field(default_factory=list)  # stale generated files deleted
    files: dict[str, str] = field(default_factory=dict)  # rel -> new content (all outputs)


def read(cfg: Config, rel: str) -> str:
    p = cfg.root / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def rtm_text(cfg: Config) -> str:
    return read(cfg, cfg.rtm)


def generated_files(cfg: Config) -> list[str]:
    """Existing files under rtm.dir that carry the generated header."""
    if not cfg.rtm_dir or not (cfg.root / cfg.rtm_dir).is_dir():
        return []
    out = []
    for dirpath, _, names in os.walk(cfg.root / cfg.rtm_dir):
        for n in names:
            p = Path(dirpath) / n
            if n.endswith(".md"):
                with p.open(encoding="utf-8", errors="replace") as fh:
                    if fh.readline().startswith(render.GEN_HEADER[:20]):
                        out.append(p.relative_to(cfg.root).as_posix())
    return sorted(out)


def _gen_edited(cfg: Config) -> list[Finding]:
    out = []
    for rel in [cfg.rtm] + generated_files(cfg):
        text = read(cfg, rel)
        for bid in render.edited_blocks(text):
            line = text[: text.find(f"rtm:begin {bid}")].count("\n") + 1
            out.append(Finding("GEN-EDITED", "P1", f"block:{bid}", rel, line,
                               f"generated block '{bid}' was edited by hand; "
                               "change the source artifact and run `rtm sync`", bid))
    return out


def check(cfg: Config) -> Result:
    g = Graph.build(cfg)
    return Result(g, checks.run(g, _gen_edited(cfg)))


def sync(cfg: Config, dry_run: bool = False) -> tuple[Result, dict[str, tuple[str, str]]]:
    """Rebuild every generated region. Returns (result, {rel: (before, after)} for changed files)."""
    g = Graph.build(cfg)
    findings = checks.run(g)
    out = render.Renderer(g, findings).all()
    res = Result(g, findings)
    diffs: dict[str, tuple[str, str]] = {}

    before = rtm_text(cfg)
    res.discarded += render.edited_blocks(before)
    after, changes = render.splice(before, out.index_blocks, out.titles)
    res.changes.update(changes)
    res.files[cfg.rtm] = after
    if after != before:
        diffs[cfg.rtm] = (before, after)

    for rel, content in out.files.items():
        old = read(cfg, rel)
        res.discarded += render.edited_blocks(old)
        res.files[rel] = content
        if old != content:
            diffs[rel] = (old, content)
            ob, nb = render.blocks(old), render.blocks(content)
            for bid, span in nb.items():
                delta = render.row_delta(ob[bid].body if bid in ob else "", span.body)
                if delta != (0, 0):
                    res.changes[bid] = delta
    for rel in generated_files(cfg):
        if rel not in out.files:
            old = read(cfg, rel)
            res.removed.append(rel)
            diffs[rel] = (old, "")
            for bid, span in render.blocks(old).items():
                res.changes[bid] = (0, len(render.rows_of(span.body)))

    if not dry_run:
        for rel, (_, new) in diffs.items():
            p = cfg.root / rel
            if new:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(new, encoding="utf-8")
            else:
                p.unlink(missing_ok=True)
                _prune_empty(p.parent, cfg.root / cfg.rtm_dir)
        state.write_set(cfg.root, "last.json", {f.fingerprint for f in findings})
    return res, diffs


def _prune_empty(d: Path, stop: Path) -> None:
    while d != stop and d.is_dir() and not any(d.iterdir()):
        d.rmdir()
        d = d.parent


def new_findings(root: Path, findings: list[Finding]) -> list[Finding]:
    base = checks.load_baseline(root)
    return [f for f in findings if f.fingerprint not in base]


def describe_changes(changes: dict[str, tuple[int, int]], limit: int = 6) -> str:
    items = sorted(changes.items())
    parts = [f"{b} +{a}/-{r}" for b, (a, r) in items[:limit]]
    if len(items) > limit:
        parts.append(f"+{len(items) - limit} more")
    return ", ".join(parts)


__all__ = ["load", "check", "sync", "new_findings", "describe_changes", "Result"]
