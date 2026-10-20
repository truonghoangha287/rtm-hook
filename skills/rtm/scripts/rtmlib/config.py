"""Load and validate rtm.config.json, plus glob helpers.

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


class ConfigError(ValueError):
    pass


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
    severity: str = "P2"
    ref_marker: str | None = None
    inherit_from: str | None = None
    children: Children | None = None
    parent: str | None = None  # set on synthetic child layers


class Config:
    def __init__(self, root: Path, raw: dict):
        self.root = root
        self.raw = raw
        self.rtm = raw.get("rtm") or _fail("'rtm' (path to rtm.md) is required")
        self.exclude = [glob_re(p) for p in raw.get("exclude", [])]
        self.layers: dict[str, Layer] = {}
        for lr in raw.get("layers", []):
            layer = _layer(lr)
            self._add(layer)
            if layer.children:
                ch = layer.children
                self._add(Layer(id=ch.id, label=ch.label, upstream=[layer.id],
                                trace_via=[layer.id], parent=layer.id, severity=layer.severity))
        if not self.layers:
            _fail("at least one layer is required")
        for layer in self.layers.values():
            for ref in layer.upstream + layer.trace_via + [x for g in layer.require for x in g]:
                if not ref.startswith("@") and ref not in self.layers:
                    _fail(f"layer '{layer.id}' refers to unknown layer '{ref}'")
            if layer.severity not in SEVERITIES:
                _fail(f"layer '{layer.id}': severity must be one of {SEVERITIES}")
        self.render = raw.get("render", {})
        self.coverage = raw.get("coverage", [])
        self.stop_block = raw.get("stop_block_severities", ["P0", "P1"])
        self.max_messages = int(raw.get("max_messages", 5))

    def _add(self, layer: Layer) -> None:
        if layer.id in self.layers:
            _fail(f"duplicate layer id '{layer.id}'")
        self.layers[layer.id] = layer

    # -- prefixes ---------------------------------------------------------
    def prefix_layer(self) -> dict[str, str]:
        return {p: l.id for l in self.layers.values() for p in l.prefixes}

    def composites(self) -> dict[str, str]:
        out = {}
        for l in self.layers.values():
            if l.children:
                for p in l.prefixes:
                    out[p] = l.children.suffix
        return out

    # -- files ------------------------------------------------------------
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
            if not any(ch in pat for ch in "*?["):
                if (self.root / pat).is_file() and not self.excluded(pat):
                    out.add(pat)
                continue
            rx, base = glob_re(pat), _literal_base(pat)
            start = self.root / base
            for dirpath, dirnames, filenames in os.walk(start):
                reldir = Path(dirpath).relative_to(self.root).as_posix()
                reldir = "" if reldir == "." else reldir + "/"
                dirnames[:] = [d for d in dirnames
                               if not d.startswith(".") and not self.excluded(reldir + d + "/")]
                for f in filenames:
                    rel = reldir + f
                    if rx.match(rel) and not self.excluded(rel):
                        out.add(rel)
        return sorted(out)

    def watched(self) -> dict[str, list[re.Pattern]]:
        """kind -> patterns. 'doc' = re-sync now; 'code' = mark dirty; 'rtm' = check."""
        doc, code = [], []
        for l in self.layers.values():
            for d in l.define:
                doc += d.files
            for a in l.attrs:
                if a.file != self.rtm:
                    doc.append(a.file)
            code += l.files
        return {"rtm": [glob_re(self.rtm)], "doc": [glob_re(p) for p in doc],
                "code": [glob_re(p) for p in code]}

    def classify(self, rel: str) -> str | None:
        if self.excluded(rel):
            return None
        for kind, pats in self.watched().items():
            if any(rx.match(rel) for rx in pats):
                return kind
        return None


def _fail(msg: str):
    raise ConfigError(msg)


def _layer(lr: dict) -> Layer:
    lid = lr.get("id") or _fail("every layer needs an 'id'")
    kind = lr.get("kind", "ids")
    if kind not in ("ids", "files"):
        _fail(f"layer '{lid}': kind must be 'ids' or 'files'")
    defines = [Define(files=d["files"], how=d.get("how", "table")) for d in lr.get("define", [])]
    for d in defines:
        if d.how not in ("table", "heading"):
            _fail(f"layer '{lid}': define.how must be 'table' or 'heading'")
    if kind == "ids" and not (lr.get("prefixes") and defines):
        _fail(f"layer '{lid}': an 'ids' layer needs 'prefixes' and 'define'")
    if kind == "files" and not lr.get("files"):
        _fail(f"layer '{lid}': a 'files' layer needs 'files'")
    ch = lr.get("children")
    children = None
    if ch:
        children = Children(id=ch["id"], label=ch.get("label", ch["id"].upper()),
                            suffix=ch["suffix"], pattern=re.compile(ch["pattern"]))
    upstream = lr.get("upstream", [])
    return Layer(
        id=lid,
        label=lr.get("label", lid.upper()),
        kind=kind,
        prefixes=lr.get("prefixes", []),
        define=defines,
        files=lr.get("files", []),
        attrs=[Attr(**a) for a in lr.get("attrs", [])],
        upstream=upstream,
        trace_via=lr.get("trace_via", upstream),
        require=lr.get("require", []),
        severity=lr.get("severity", "P2"),
        ref_marker=lr.get("ref_marker"),
        inherit_from=lr.get("inherit_from"),
        children=children,
    )


def find_root(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / CONFIG_NAME).is_file():
            return d
    return None


def load(root: Path) -> Config:
    path = root / CONFIG_NAME
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path}: {e}") from e
    return Config(root, raw)
