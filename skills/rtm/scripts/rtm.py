#!/usr/bin/env python3
"""rtm — keep a Requirements Traceability Matrix in sync with the artifacts it traces.

  rtm.py sync   [--dry-run] [--diff]          regenerate the generated blocks of rtm.md
  rtm.py check  [--json] [--gate] [--new] [--file PATH] [--limit N]
  rtm.py baseline                             accept today's findings as known debt
  rtm.py why ID                               full chain up and down for one ID or file
  rtm.py stats                                node / link counts per layer

Root = --root, else the nearest dir with rtm.config.json above the cwd, else $CLAUDE_PROJECT_DIR.
Exit codes: 0 ok, 1 gate failed (P0/P1 present), 2 usage/config error.
"""
from __future__ import annotations

import argparse
import difflib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rtmlib import checks, core  # noqa: E402
from rtmlib.config import ConfigError, find_root, load  # noqa: E402


def resolve_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    starts = [Path.cwd()]
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        starts.append(Path(os.environ["CLAUDE_PROJECT_DIR"]))
    for start in starts:
        if r := find_root(start.resolve()):
            return r
    raise ConfigError("no rtm.config.json found (use --root or create one; see references/config.md)")


def cmd_sync(cfg, a) -> int:
    before = core.rtm_text(cfg)
    res, after = core.sync(cfg, dry_run=a.dry_run or a.diff)
    if a.diff:
        sys.stdout.writelines(difflib.unified_diff(
            before.splitlines(True), after.splitlines(True), cfg.rtm, cfg.rtm + " (synced)"))
        return 0
    verb = "would change" if a.dry_run else "updated"
    if res.changes:
        print(f"{cfg.rtm} {verb}: {core.describe_changes(res.changes)}")
    else:
        print(f"{cfg.rtm} already up to date")
    if res.discarded:
        print(f"note: overwrote hand edits in generated block(s): {', '.join(res.discarded)}")
    c = checks.summary(res.findings)
    print("findings: " + ", ".join(f"{k}={v}" for k, v in c.items()) + "  (rtm check for details)")
    return 0


def cmd_check(cfg, a) -> int:
    res = core.check(cfg)
    fs = res.findings
    if a.new:
        fs = core.new_findings(cfg.root, fs)
    if a.file:
        rel = cfg.rel(a.file) or a.file
        fs = [f for f in fs if f.file == rel]
    gate_fail = any(f.severity in ("P0", "P1") for f in fs)
    if a.json:
        print(checks.as_json(fs, gate_fail))
    else:
        for f in fs[: a.limit] if a.limit else fs:
            print(f.text())
        if a.limit and len(fs) > a.limit:
            print(f"… {len(fs) - a.limit} more")
        c = checks.summary(fs)
        print(("FAIL" if gate_fail else "PASS") + ": " + ", ".join(f"{k}={v}" for k, v in c.items()))
    return 1 if (a.gate and gate_fail) else 0


def cmd_baseline(cfg, a) -> int:
    res = core.check(cfg)
    p = checks.save_baseline(cfg.root, res.findings)
    print(f"baseline: {len(res.findings)} finding(s) recorded in {p.relative_to(cfg.root)}")
    return 0


def cmd_why(cfg, a) -> int:
    from rtmlib.graph import Graph
    g = Graph.build(cfg)
    k = a.id
    if k not in g.nodes:
        rel = cfg.rel(k)
        hits = g.scanner.syntax.find(k)
        k = rel if rel in g.nodes else (hits[0].key if hits else k)
    n = g.nodes.get(k)
    if not n:
        print(f"{a.id}: not defined in any configured artifact")
        return 2
    print(f"{g.show(k)}  [{cfg.layers[n.layer].label}]  {n.file}:{n.line}  {n.label[:70]}")
    if src := g.source(n):
        print(f"  source: {src}")
    for title, groups in (("upstream", g.ancestors(k)), ("downstream", g.descendants(k))):
        print(f"  {title}:")
        if not groups:
            print("    (none)")
        for lid in cfg.layers:
            ks = groups.get(lid)
            if ks:
                print(f"    {cfg.layers[lid].label:<8} {', '.join(g.show(x) for x in ks)}")
    return 0


def cmd_stats(cfg, a) -> int:
    from rtmlib.graph import Graph
    g = Graph.build(cfg)
    for lid, layer in cfg.layers.items():
        nodes = g.layer_nodes(lid)
        links = sum(len(g.parents(n)) for n in nodes)
        print(f"{layer.label:<10} {len(nodes):>5} nodes  {links:>6} upstream links")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rtm", description=__doc__.split("\n")[1])
    ap.add_argument("--root")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--diff", action="store_true", help="print the unified diff, write nothing")
    c = sub.add_parser("check")
    c.add_argument("--json", action="store_true")
    c.add_argument("--gate", action="store_true", help="exit 1 on any P0/P1")
    c.add_argument("--new", action="store_true", help="hide findings recorded in the baseline")
    c.add_argument("--file", help="only findings located in this file")
    c.add_argument("--limit", type=int, default=0)
    sub.add_parser("baseline")
    w = sub.add_parser("why")
    w.add_argument("id")
    sub.add_parser("stats")
    a = ap.parse_args(argv)
    try:
        cfg = load(resolve_root(a.root))
    except ConfigError as e:
        print(f"rtm: config error: {e}", file=sys.stderr)
        return 2
    return {"sync": cmd_sync, "check": cmd_check, "baseline": cmd_baseline,
            "why": cmd_why, "stats": cmd_stats}[a.cmd](cfg, a)


if __name__ == "__main__":
    sys.exit(main())
