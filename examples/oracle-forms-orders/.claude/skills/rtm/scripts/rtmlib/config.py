"""Load and validate rtm.config.json (schema 2: a flow of steps), plus glob helpers.

Each flow step says what it PRODUCES (ID prefixes defined in artifact files, or one node per
file) and what it CONSUMES (upstream steps it must cite, with rule all|any). Steps are mapped
onto internal `Layer`s used by the scanner, graph, checks and renderer.
See ../../references/config.md for the schema.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_NAME = "rtm.config.json"
SEVERITIES = ("P0", "P1", "P2", "P3")
VAR = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ConfigError(ValueError):
    pass


def _fail(msg: str):
    raise ConfigError(msg)


def glob_re(pattern: str) -> re.Pattern:
    """Glob -> regex over POSIX relative paths. `**/` spans dirs, `*` does not."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def _literal_base(pattern: str) -> str:
    parts = []
    for part in pattern.split("/")[:-1]:
        if any(ch in part for ch in "*?["):
            break
        parts.append(part)
    return "/".join(parts)


def is_glob(p: str) -> bool:
    return any(ch in p for ch in "*?[")


@dataclass
class Define:
    files: list[str]
    how: str  # "table" | "heading"


@dataclass
class Attr:
    name: str
    file: str
    key_col: str
    value_col: str


@dataclass
class Children:
    id: str
    label: str
    suffix: str
    pattern: re.Pattern
    example: str = ""


@dataclass
class Layer:
    id: str
    label: str
    kind: str = "ids"  # "ids" | "files"
    prefixes: list[str] = field(default_factory=list)
    define: list[Define] = field(default_factory=list)
    files: list[str] = field(default_factory=list)  # kind == files
    attrs: list[Attr] = field(default_factory=list)
    upstream: list[str] = field(default_factory=list)
    trace_via: list[str] = field(default_factory=list)
    require: list[list[str]] = field(default_factory=list)
    rule: str = "any"
    severity: str = "P2"
    ref_marker: str | None = None
    inherit_from: str | None = None
    children: Children | None = None
    parent: str | None = None  # set on synthetic child layers


class Config:
    def __init__(self, root: Path, raw: dict):
        self.root = root
        self.raw = raw
        if raw.get("schema") != 2 or "flow" not in raw:
            _fail("expected schema 2 with a 'flow' list (see references/config.md)")
        self.vars: dict[str, str] = {k: str(v) for k, v in (raw.get("vars") or {}).items()}
        unset = [k for k, v in self.vars.items() if v.startswith("<") and v.endswith(">")]
        if unset:
            _fail(f"vars not set: {', '.join(unset)} (use `rtm.py init --set {unset[0]}=…`)")
        r = raw.get("rtm") or {}
        self.rtm = self.sub(r.get("index") or _fail("rtm.index (path of the RTM index file) is required"))
        self.rtm_dir = self.sub(r["dir"]).rstrip("/") if r.get("dir") else None
        self.shard_size = int(r.get("shard_size", 0))
        self.max_list = int(r.get("max_list", 6))
        self.count_only = set(r.get("count_only", []))
        self.exclude = [glob_re(self.sub(p)) for p in raw.get("exclude", [])]
        self.layers: dict[str, Layer] = {}
        self.order: list[str] = []  # flow order incl. child steps right after their parent
        for st in raw["flow"]:
            layer = self._step(st)
            self._add(layer)
            if layer.children:
                ch = layer.children
                self._add(Layer(id=ch.id, label=ch.label, upstream=[layer.id], trace_via=[layer.id],
                                require=[], parent=layer.id, severity=layer.severity))
        if not self.layers:
            _fail("the flow needs at least one step")
        self._validate()
        self.coverage = raw.get("coverage", [])
        for c in self.coverage:
            for k in ("from", "to"):
                if c.get(k) not in self.layers:
                    _fail(f"coverage.{k}: unknown step '{c.get(k)}'")
        self.status = raw.get("status", {})
        self.stop_block = raw.get("stop_block_severities", ["P0", "P1"])
        self.max_messages = int(raw.get("max_messages", 5))
        self.views_raw = raw.get("views", "auto")

    # -- vars ---------------------------------------------------------------
    def sub(self, s: str) -> str:
        def rep(m):
            if m.group(1) not in self.vars:
                _fail(f"unknown var {{{m.group(1)}}} in '{s}'")
            return self.vars[m.group(1)].rstrip("/")
        return VAR.sub(rep, s)

    # -- steps --------------------------------------------------------------
    def _step(self, st: dict) -> Layer:
        sid = st.get("step") or _fail("every flow item needs a 'step' id")
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", sid):
            _fail(f"step id '{sid}': use lowercase letters, digits, - or _")
        prod, cons = st.get("produces") or {}, st.get("consumes") or {}
        has_ids, has_files = bool(prod.get("ids")), bool(prod.get("files"))
        if has_ids == has_files:
            _fail(f"step '{sid}': produces needs exactly one of 'ids' (+ 'in') or 'files'")
        defines = []
        for d in prod.get("in", []):
            how = d.get("how", "table")
            if how not in ("table", "heading"):
                _fail(f"step '{sid}': produces.in.how must be 'table' or 'heading'")
            defines.append(Define([self.sub(f) for f in d.get("files", [])], how))
        if has_ids and not defines:
            _fail(f"step '{sid}': produces.in (where the IDs are defined) is required")
        for p in prod.get("ids", []):
            if not re.fullmatch(r"[A-Z][A-Za-z0-9]{0,9}", p):
                _fail(f"step '{sid}': bad ID prefix '{p}' (letters/digits, starting uppercase)")
        children = None
        if ch := prod.get("children"):
            if not has_ids:
                _fail(f"step '{sid}': children need an ids step")
            try:
                pat = re.compile(ch["pattern"])
            except (KeyError, re.error) as e:
                _fail(f"step '{sid}': children.pattern invalid: {e}")
            if pat.groups < 1:
                _fail(f"step '{sid}': children.pattern must capture the child number")
            ex = ch.get("example", "")
            if ex and not pat.search(ex.replace("{n}", "1")):
                _fail(f"step '{sid}': children.example does not match children.pattern")
            children = Children(ch.get("step") or _fail(f"step '{sid}': children.step is required"),
                                ch.get("label", ch["step"].upper()), ch.get("suffix") or
                                _fail(f"step '{sid}': children.suffix is required"), pat, ex)
        steps = cons.get("steps", [])
        attrs = cons.get("attrs", [])
        rule = cons.get("rule", "any")
        if rule not in ("all", "any"):
            _fail(f"step '{sid}': consumes.rule must be 'all' or 'any'")
        if "require" in cons:
            require = cons["require"]
        elif rule == "all":
            require = [[s] for s in steps] + [["@" + a] for a in attrs]
        else:
            require = [steps + ["@" + a for a in attrs]] if (steps or attrs) else []
        attr_defs = []
        for name, a in (st.get("attrs") or {}).items():
            src = a.get("from", "index")
            attr_defs.append(Attr(name, self.rtm if src == "index" else self.sub(src),
                                  a.get("key_col", "ID"), a.get("value_col", name.title())))
        missing = [a for a in attrs if a not in {x.name for x in attr_defs}]
        if missing:
            _fail(f"step '{sid}': consumes.attrs {missing} has no matching 'attrs' definition")
        sev = st.get("severity", "P2")
        if sev not in SEVERITIES:
            _fail(f"step '{sid}': severity must be one of {SEVERITIES}")
        return Layer(
            id=sid, label=st.get("label", sid.upper()),
            kind="ids" if has_ids else "files",
            prefixes=prod.get("ids", []), define=defines,
            files=[self.sub(f) for f in prod.get("files", [])],
            attrs=attr_defs, upstream=steps, trace_via=cons.get("walk", steps),
            require=require, rule=rule, severity=sev,
            ref_marker=cons.get("marker"), inherit_from=prod.get("inherit_from"),
            children=children)

    def _add(self, layer: Layer) -> None:
        if layer.id in self.layers:
            _fail(f"duplicate step id '{layer.id}'")
        self.layers[layer.id] = layer
        self.order.append(layer.id)

    def _validate(self) -> None:
        owner: dict[str, str] = {}
        for l in self.layers.values():
            for p in l.prefixes:
                if p in owner:
                    _fail(f"ID prefix '{p}' is produced by both '{owner[p]}' and '{l.id}'")
                owner[p] = l.id
            for ref in l.upstream + l.trace_via + [x for g in l.require for x in g]:
                if not ref.startswith("@") and ref not in self.layers:
                    _fail(f"step '{l.id}' consumes unknown step '{ref}'")
            bad = [w for w in l.trace_via if w not in l.upstream]
            if bad:
                _fail(f"step '{l.id}': consumes.walk {bad} must be a subset of consumes.steps")
        # cycles (self-loops allowed, e.g. INT citing CMP inside one HLD step)
        state: dict[str, int] = {}

        def visit(n: str, path: list[str]):
            state[n] = 1
            for u in self.layers[n].upstream:
                if u == n:
                    continue
                if state.get(u) == 1:
                    _fail("cycle in consumes: " + " → ".join(path + [n, u]))
                if not state.get(u):
                    visit(u, path + [n])
            state[n] = 2
        for n in self.layers:
            if not state.get(n):
                visit(n, [])

    # -- prefixes -----------------------------------------------------------
    def prefix_layer(self) -> dict[str, str]:
        return {p: l.id for l in self.layers.values() for p in l.prefixes}

    def composites(self) -> dict[str, str]:
        return {p: l.children.suffix for l in self.layers.values() if l.children for p in l.prefixes}

    # -- files --------------------------------------------------------------
    def rel(self, path: str | os.PathLike) -> str | None:
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        try:
            return p.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return None

    def excluded(self, rel: str) -> bool:
        return any(rx.match(rel) for rx in self.exclude)

    def expand(self, patterns: list[str]) -> list[str]:
        out: set[str] = set()
        for pat in patterns:
            if not is_glob(pat):
                if (self.root / pat).is_file() and not self.excluded(pat) and not self.generated(pat):
                    out.add(pat)
                continue
            rx, base = glob_re(pat), _literal_base(pat)
            for dirpath, dirnames, filenames in os.walk(self.root / base):
                reldir = Path(dirpath).relative_to(self.root).as_posix()
                reldir = "" if reldir == "." else reldir + "/"
                dirnames[:] = [d for d in dirnames
                               if not d.startswith(".") and not self.excluded(reldir + d + "/")]
                for f in filenames:
                    rel = reldir + f
                    if rx.match(rel) and not self.excluded(rel) and not self.generated(rel):
                        out.add(rel)
        return sorted(out)

    def generated(self, rel: str) -> bool:
        return bool(self.rtm_dir) and rel.startswith(self.rtm_dir + "/")

    def classify(self, rel: str) -> str | None:
        """config | rtm | generated | doc (re-sync now) | code (mark dirty) | None."""
        if rel == CONFIG_NAME:
            return "config"
        if rel == self.rtm:
            return "rtm"
        if self.generated(rel):
            return "generated"
        if self.excluded(rel):
            return None
        for l in self.layers.values():
            if any(glob_re(p).match(rel) for d in l.define for p in d.files):
                return "doc"
            if any(a.file != self.rtm and glob_re(a.file).match(rel) for a in l.attrs):
                return "doc"
        for l in self.layers.values():
            if any(glob_re(p).match(rel) for p in l.files):
                return "code"
        return None


def find_root(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / CONFIG_NAME).is_file():
            return d
    return None


def read_raw(root: Path) -> dict:
    path = root / CONFIG_NAME
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path}: {e}") from e


def load(root: Path) -> Config:
    return Config(root, read_raw(root))
