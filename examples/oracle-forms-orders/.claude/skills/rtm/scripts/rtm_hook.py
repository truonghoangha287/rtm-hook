#!/usr/bin/env python3
"""Claude Code hook for the RTM.  Usage (settings.json):  rtm_hook.py pre|post|stop

pre   PreToolUse  Write|Edit|MultiEdit  deny edits to generated section files, or to generated
                                        blocks of the RTM index
post  PostToolUse Write|Edit|MultiEdit  step artifact (doc) -> sync + report new findings;
                                        code/test -> mark dirty only; index -> check;
                                        rtm.config.json -> validate + re-sync (flow change)
stop  Stop                              if anything is dirty: sync; block the stop on new
                                        P0/P1 findings introduced this session

Silent (no output, ~0 tokens) unless something changed or a new problem appeared.
Never fails the tool call: internal errors are reported as a systemMessage.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def emit(obj: dict) -> None:
    print(json.dumps(obj))


def root_of(inp: dict) -> Path | None:
    from rtmlib.config import CONFIG_NAME
    for cand in (os.environ.get("CLAUDE_PROJECT_DIR"), inp.get("cwd")):
        if cand and (Path(cand) / CONFIG_NAME).is_file():
            return Path(cand)
    return None


def fmt(findings, limit: int) -> str:
    lines = [f.text() for f in findings[:limit]]
    if len(findings) > limit:
        lines.append(f"… {len(findings) - limit} more — run `rtm check --new`")
    return "\n".join(lines)


def edit_spans(tool: str, ti: dict, current: str):
    """Yield (start, end) char ranges of `current` that the edit would replace."""
    edits = ti.get("edits") if tool == "MultiEdit" else [ti]
    for e in edits or []:
        old = e.get("old_string") or ""
        if not old:
            continue
        i = current.find(old)
        while i != -1:
            yield i, i + len(old)
            if not e.get("replace_all"):
                break
            i = current.find(old, i + 1)


DENY = ("is generated. Change the source artifact (the step's doc, code `TASK-`-style refs or "
        "test marker lines) instead — the RTM re-syncs automatically. Ask questions with "
        "`rtm.py why <ID>` / `rtm.py query …`. Text outside rtm:begin/end markers in the index is editable.")


def deny(what: str) -> None:
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                 "permissionDecisionReason": f"RTM {what} {DENY}"}})


def pre(inp, cfg) -> None:
    from rtmlib import render
    tool, ti = inp.get("tool_name"), inp.get("tool_input") or {}
    rel = cfg.rel(ti.get("file_path", ""))
    if rel and cfg.generated(rel):
        return deny(f"section file '{rel}'")
    if rel != cfg.rtm:
        return
    path = cfg.root / cfg.rtm
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    spans = render.blocks(current)
    hit = None
    if tool == "Write":
        new = render.blocks(ti.get("content", ""))
        hit = next((b for b in spans if b not in new or new[b].body != spans[b].body), None)
    else:
        for s, e in edit_spans(tool, ti, current):
            hit = next((b.id for b in spans.values() if s < b.end and e > b.start), None)
            if hit:
                break
    if hit:
        deny(f"block '{hit}'")


def post(inp, cfg) -> None:
    from rtmlib import checks, core, state
    rel = cfg.rel((inp.get("tool_input") or {}).get("file_path", ""))
    kind = cfg.classify(rel) if rel else None
    if kind in (None, "generated", "config"):
        return
    root = cfg.root
    if state.mark_dirty(root, rel):  # first touch this turn: remember the pre-edit state
        state.write_set(root, "start.json", state.read_set(root, "last.json") or set())
    if kind == "code":
        return  # cheap path; the Stop hook syncs once per turn
    last = state.read_set(root, "last.json") or set()
    if kind == "doc":
        res, _ = core.sync(cfg)
    else:  # rtm.md hand sections edited
        res = core.check(cfg)
    base = checks.load_baseline(root)
    new = [f for f in res.findings if f.fingerprint not in last and f.fingerprint not in base]
    parts = []
    if res.changes:
        parts.append(f"RTM synced ({core.describe_changes(res.changes)}).")
    if new:
        parts.append("New RTM findings:\n" + fmt(new, cfg.max_messages))
    if parts:
        emit({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                     "additionalContext": "\n".join(parts)}})


def config_changed(root: Path) -> None:
    """The flow itself was edited: validate, re-sync, and don't let Stop blame the change."""
    from rtmlib import checks, core, state
    from rtmlib.config import ConfigError, load
    try:
        cfg = load(root)
    except ConfigError as e:
        emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext":
              f"rtm.config.json is invalid, RTM not synced: {e}"}})
        return
    res, diffs = core.sync(cfg)
    fps = {f.fingerprint for f in res.findings}
    state.write_set(root, "start.json", fps)  # findings caused by the flow change aren't "new"
    new = core.new_findings(root, res.findings)
    msg = f"RTM flow changed: {len(diffs)} file(s) re-synced ({core.describe_changes(res.changes)})."
    if res.removed:
        msg += f" Removed {len(res.removed)} stale section file(s)."
    if new:
        msg += (f" {len(new)} finding(s) are not in the baseline — review with `rtm.py check --new`; "
                f"if the user accepts them, run `rtm.py baseline`. Verify the flow with `rtm.py selftest`.")
    emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}})


def stop(inp, cfg) -> None:
    from rtmlib import checks, core, state
    root = cfg.root
    if not state.dirty(root):
        return
    start = state.read_set(root, "start.json") or set()
    res, _ = core.sync(cfg)
    base = checks.load_baseline(root)
    blocking = [f for f in res.findings
                if f.severity in cfg.stop_block
                and f.fingerprint not in start and f.fingerprint not in base]
    if blocking and not inp.get("stop_hook_active"):
        emit({"decision": "block", "reason":
              "RTM check found new traceability problems from this session. Fix them in the "
              "source artifact (not in rtm.md), or tell the user why they are intended:\n"
              + fmt(blocking, cfg.max_messages)})
        return
    state.clear(root)
    msg = f"RTM synced: {core.describe_changes(res.changes)}" if res.changes else ""
    if blocking:
        msg += f"{' — ' if msg else 'RTM: '}{len(blocking)} new P0/P1 finding(s) left open"
    if msg:
        emit({"systemMessage": msg})  # shown to the user, not sent to the model


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        inp = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    try:
        root = root_of(inp)
        if not root:
            return 0  # project has no rtm.config.json: hook is a no-op
        from rtmlib.config import CONFIG_NAME, load
        fp = (inp.get("tool_input") or {}).get("file_path") or ""
        if mode == "post" and fp and Path(fp).name == CONFIG_NAME and \
                Path(fp).resolve().parent == root.resolve():
            config_changed(root)
            return 0
        cfg = load(root)
        {"pre": pre, "post": post, "stop": stop}.get(mode, lambda *_: None)(inp, cfg)
    except Exception as e:  # never break the user's tool call
        emit({"systemMessage": f"rtm hook ({mode}) error: {type(e).__name__}: {e}"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
