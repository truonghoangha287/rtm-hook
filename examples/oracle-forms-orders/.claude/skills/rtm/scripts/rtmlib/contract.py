"""Contract suite generated from a flow. Used by `rtm.py selftest` and tests/test_flows.py.

Every case builds a fresh synthetic repo (synth.py) in a temp dir — the real repo is never
touched — and checks one promise of the flow. `run(raw)` returns a list of Case results.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import checks, core, flow, query, render, synth
from .config import CONFIG_NAME, Config, ConfigError
from .graph import Graph

HOOK = Path(__file__).resolve().parents[1] / "rtm_hook.py"


@dataclass
class Case:
    name: str
    ok: bool
    detail: str = ""


class _Tmp:
    def __init__(self):
        self._t = tempfile.TemporaryDirectory(prefix="rtm-selftest-")
        self.path = Path(self._t.name)
        self.n = 0

    def new(self) -> Path:
        self.n += 1
        return self.path / f"r{self.n}"

    def close(self):
        self._t.cleanup()


def _hook(root: Path, mode: str, payload: dict) -> dict | None:
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)}
    r = subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps({"cwd": str(root), **payload}),
                       capture_output=True, text=True, env=env, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"hook {mode} exit {r.returncode}: {r.stderr[-300:]}")
    return json.loads(r.stdout) if r.stdout.strip() else None


def _edit(root: Path, rel: str, old: str, new: str) -> dict:
    p = root / rel
    text = p.read_text()
    p.write_text(text.replace(old, new, 1) if old else text + new)
    return {"tool_name": "Edit", "tool_input": {"file_path": str(p), "old_string": old or "x",
                                                "new_string": new}}


def run(raw: dict) -> list[Case]:
    out: list[Case] = []
    tmp = _Tmp()

    def case(name):
        def deco(fn):
            try:
                res = fn()
                ok, detail = (res if isinstance(res, tuple) else (bool(res), ""))
            except Exception as e:  # a crash is a failed contract, not a crashed suite
                ok, detail = False, f"{type(e).__name__}: {e}"
            out.append(Case(name, ok, detail))
            return fn
        return deco

    try:
        try:
            base = synth.build(raw, tmp.new())
        except ConfigError as e:
            return [Case("flow is valid", False, str(e))]
        cfg, L = base.cfg, base.cfg.layers
        out.append(Case("flow is valid", True, f"{len(cfg.order)} steps"))

        @case("synthetic repo is clean (0 P0/P1, doctor quiet)")
        def _():
            res = core.check(cfg)
            bad = [f.text() for f in res.findings if f.severity in ("P0", "P1")
                   or f.rule in ("MISSING-UPSTREAM", "DANGLING")]
            warn = flow.doctor(cfg, res.graph)
            return (not bad and not warn), "; ".join(bad[:3] + warn[:3])

        @case("every step finds its synthetic nodes")
        def _():
            g = Graph.build(cfg)
            miss = [s for s in cfg.order if len(g.layer_nodes(s)) != len(base.keys[s])]
            return not miss, f"count mismatch in {miss}" if miss else ""

        @case("sync is idempotent")
        def _():
            core.sync(cfg)
            first = {p: core.read(cfg, p) for p in [cfg.rtm] + core.generated_files(cfg)}
            res, diffs = core.sync(cfg)
            return (not diffs and not res.changes), f"second sync changed {list(diffs)[:3]}"

        @case("views follow the flow (one output per view, TOC complete)")
        def _():
            views = render.resolve_views(cfg)
            res, _ = core.sync(cfg)
            files = core.generated_files(cfg)
            index = core.rtm_text(cfg)
            missing = []
            for v in views:
                if v["type"] == "toc" and not cfg.rtm_dir:
                    continue
                if v.get("file") and cfg.rtm_dir:
                    if not any(f == f"{cfg.rtm_dir}/{v['file']}.md" or
                               f.startswith(f"{cfg.rtm_dir}/{v['file']}/") for f in files):
                        missing.append(v["id"])
                elif f"rtm:begin {v['id']} " not in index:
                    missing.append(v["id"])
            toc_ok = not cfg.rtm_dir or all(Path(f).name in index for f in files)
            return (not missing and toc_ok), f"missing views {missing}; toc ok={toc_ok}"

        if cfg.rtm_dir:
            @case("large views shard by ID range and stale shards are removed")
            def _():
                r2 = copy.deepcopy(synth.synth_vars(raw))
                r2.setdefault("rtm", {})["shard_size"] = 1
                s2 = synth.build(r2, tmp.new())
                core.sync(s2.cfg)
                sharded = [f for f in core.generated_files(s2.cfg) if f.count("/") > cfg.rtm_dir.count("/") + 1]
                r2["rtm"]["shard_size"] = 0
                (s2.root / CONFIG_NAME).write_text(json.dumps(r2))
                cfg2 = Config(s2.root, r2)
                res, _ = core.sync(cfg2)
                left = [f for f in core.generated_files(cfg2) if f in sharded]
                return (bool(sharded) and not left), f"shards={len(sharded)} left after unshard={left[:2]}"

        for sid in cfg.order:
            l = L[sid]
            for gi, g in enumerate(l.require):
                @case(f"[{sid}] dropping '{' or '.join(g)}' raises MISSING-UPSTREAM {l.severity}")
                def _(sid=sid, gi=gi, l=l):
                    s = synth.build(raw, tmp.new(), drop=(sid, gi))
                    res = core.check(s.cfg)
                    want = s.node0(sid)
                    hit = [f for f in res.findings if f.rule == "MISSING-UPSTREAM"
                           and res.graph.show(f.subject) in (want, Path(want).stem)
                           and f.severity == l.severity]
                    return bool(hit), f"no finding for {want}"
                if len(g) > 1:
                    @case(f"[{sid}] 'any' rule accepts '{g[-1]}' instead of '{g[0]}'")
                    def _(sid=sid, gi=gi):
                        s = synth.build(raw, tmp.new(), alt=(sid, gi))
                        res = core.check(s.cfg)
                        bad = [f.text() for f in res.findings if f.rule == "MISSING-UPSTREAM"]
                        return not bad, "; ".join(bad[:2])
            if l.prefixes or l.parent:
                @case(f"[{sid}] an undefined {l.label} ID is reported as DANGLING P0")
                def _(sid=sid):
                    s = synth.build(raw, tmp.new(), dangle=sid)
                    bad = s.dangling.get(sid)
                    res = core.check(s.cfg)
                    hit = [f for f in res.findings if f.rule == "DANGLING" and f.severity == "P0"
                           and res.graph.syntax.show(f.detail) == bad]
                    return bool(hit), f"{bad} not reported"
            if l.children:
                @case(f"[{sid}] uncovered {l.children.label}s show in the coverage view and `query gaps`")
                def _(l=l):
                    res = core.check(cfg)
                    ch = l.children.id
                    views = [v for v in render.resolve_views(cfg) if v["type"] == "children"
                             and v["parent"] == l.id]
                    if not views:
                        return False, "no coverage view generated"
                    gaps = query.gaps(res.graph, ch, views[0]["target"])
                    want = [k for k in base.keys[ch] if k.endswith(f"{l.children.suffix}2")]
                    got = {r["id"] for r in gaps}
                    return set(want) <= got, f"gaps {sorted(got)[:4]} missing {want[:2]}"

        # -- hooks -------------------------------------------------------------------
        @case("hooks: generated output is write-protected, hand text is not")
        def _():
            s = synth.build(raw, tmp.new())
            core.sync(s.cfg)
            gen = core.generated_files(s.cfg)
            target = gen[0] if gen else s.cfg.rtm
            text = (s.root / target).read_text()
            row = next(l for l in text.splitlines() if l.startswith("| ") and "---" not in l)
            deny = _hook(s.root, "pre", {"tool_name": "Edit", "tool_input": {
                "file_path": str(s.root / target), "old_string": row, "new_string": row + " x"}})
            allow = _hook(s.root, "pre", {"tool_name": "Edit", "tool_input": {
                "file_path": str(s.root / s.cfg.rtm), "old_string": "# Synthetic", "new_string": "# Hand"}})
            ok = (deny or {}).get("hookSpecificOutput", {}).get("permissionDecision") == "deny" and allow is None
            return ok, f"deny={deny} allow={allow}"

        @case("hooks: editing a step's artifact re-syncs the matrix")
        def _():
            s = synth.build(raw, tmp.new())
            core.sync(s.cfg)
            checks.save_baseline(s.root, core.check(s.cfg).findings)
            sid = next(x for x in s.cfg.order if L[x].kind == "ids" and not L[x].parent)
            l, path = s.cfg.layers[sid], s.where[sid]
            new_id = f"{l.prefixes[0]}-050"
            first = s.keys[sid][0]
            text = (s.root / path).read_text()
            if f"| {first} |" in text:
                p = _edit(s.root, path, f"| {first} |", f"| {new_id} | Added | — |\n| {first} |")
            else:
                p = _edit(s.root, path, "", f"\n## {new_id} — Added\n")
            out_ = _hook(s.root, "post", p)
            ctx = (out_ or {}).get("hookSpecificOutput", {}).get("additionalContext", "")
            return "RTM synced" in ctx, ctx[:200]

        @case("hooks: Stop blocks a new P0 once, never loops, ignores baselined debt")
        def _():
            s = synth.build(raw, tmp.new())
            core.sync(s.cfg)
            checks.save_baseline(s.root, core.check(s.cfg).findings)
            sid = s.cfg.order[-1]
            if L[sid].parent or L[sid].kind != "files":
                sid = next((x for x in reversed(s.cfg.order) if L[x].kind == "files"), sid)
            some = next(x for x in s.cfg.order if L[x].prefixes)
            bad = f"{L[some].prefixes[0]}-999"
            path = s.where[sid]
            if L[sid].kind == "files":
                p = _edit(s.root, path, "", f"// {L[sid].ref_marker or 'see'} {bad}\n")
            else:
                p = _edit(s.root, path, "", f"\nSee {bad}\n")
            _hook(s.root, "post", p)
            blocked = _hook(s.root, "stop", {"stop_hook_active": False}) or {}
            looped = _hook(s.root, "stop", {"stop_hook_active": True}) or {}
            s3 = synth.build(raw, tmp.new())
            core.sync(s3.cfg)
            checks.save_baseline(s3.root, core.check(s3.cfg).findings)
            p3 = _edit(s3.root, s3.where[sid], "", "\n")
            _hook(s3.root, "post", p3)
            clean = _hook(s3.root, "stop", {"stop_hook_active": False}) or {}
            ok = (blocked.get("decision") == "block" and bad in blocked.get("reason", "")
                  and looped.get("decision") != "block" and clean.get("decision") != "block")
            return ok, f"blocked={blocked.get('decision')} looped={looped.get('decision')} clean={clean.get('decision')}"

        # -- flow changes ------------------------------------------------------------
        consumed = {u for x in cfg.order for u in L[x].upstream if u != x}
        last = cfg.order[-1]
        if len([x for x in cfg.order if not L[x].parent]) > 2 and last not in consumed and not L[last].parent:
            @case(f"flow change: removing step '{last}' re-shapes views without blocking Stop")
            def _():
                s = synth.build(raw, tmp.new())
                core.sync(s.cfg)
                checks.save_baseline(s.root, core.check(s.cfg).findings)
                before = set(core.generated_files(s.cfg))
                r2 = json.loads((s.root / CONFIG_NAME).read_text())
                r2["flow"] = [x for x in r2["flow"] if x["step"] != last]
                r2["coverage"] = [c for c in r2.get("coverage", []) if last not in (c["from"], c["to"])]
                if isinstance(r2.get("views"), dict):
                    r2["views"]["add"] = [v for v in r2["views"].get("add", [])
                                          if f'"{last}"' not in json.dumps(v)]
                cfgp = s.root / CONFIG_NAME
                cfgp.write_text(json.dumps(r2, indent=1))
                msg = _hook(s.root, "post", {"tool_name": "Write", "tool_input": {"file_path": str(cfgp)}})
                stop = _hook(s.root, "stop", {"stop_hook_active": False}) or {}
                cfg2 = Config(s.root, r2)
                gone = [f for f in before if f"-{last}" in f and f not in core.generated_files(cfg2)]
                old_view = any(f"backward-{last}" in f for f in before)
                ok = stop.get("decision") != "block" and msg is not None and (gone or not old_view)
                return ok, f"stop={stop.get('decision')} msg={(msg or {})} gone={gone[:2]}"

        @case("flow change: adding a step adds its views and passes its own rules")
        def _():
            s = synth.build(raw, tmp.new())
            core.sync(s.cfg)
            r2 = json.loads((s.root / CONFIG_NAME).read_text())
            first = next(x for x in cfg.order if L[x].kind == "ids" and not L[x].parent)
            r2["flow"].append({"step": "zz-extra", "label": "Extra", "severity": "P1",
                               "produces": {"files": ["zz-extra/*.txt"]},
                               "consumes": {"steps": [first], "marker": "Covers:"}})
            (s.root / "zz-extra").mkdir()
            (s.root / "zz-extra/a.txt").write_text(f"Covers: {s.keys[first][0]}\n")
            (s.root / CONFIG_NAME).write_text(json.dumps(r2))
            cfg2 = Config(s.root, r2)
            res, _ = core.sync(cfg2)
            views = {v["id"] for v in render.resolve_views(cfg2)}
            bad = [f.text() for f in res.findings if f.subject.startswith("zz-extra")]
            return ("backward-zz-extra" in views and not bad), f"views={sorted(views)} bad={bad[:2]}"
    finally:
        tmp.close()
    return out
