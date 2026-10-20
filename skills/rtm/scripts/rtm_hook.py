#!/usr/bin/env python3
"""Claude Code hook for the RTM.  Usage (settings.json):  rtm_hook.py pre|post|stop

pre   PreToolUse  Write|Edit|MultiEdit  deny edits that touch a generated block of rtm.md
post  PostToolUse Write|Edit|MultiEdit  doc layer -> sync + report new findings;
                                        code/test -> mark dirty only; rtm.md -> check
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


def pre(inp, cfg) -> None:
    from rtmlib import render
    tool, ti = inp.get("tool_name"), inp.get("tool_input") or {}
    if cfg.rel(ti.get("file_path", "")) != cfg.rtm:
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
        emit({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason":
                f"RTM block '{hit}' is generated. Change the source artifact (BRD/FRD, stories, "
                f"HLD, LLD, code `TASK-` refs or test `Verifies:` lines) instead — the RTM re-syncs "
                f"automatically. Text outside the rtm:begin/end markers is editable."}})


def post(inp, cfg) -> None:
    from rtmlib import checks, core, state
    rel = cfg.rel((inp.get("tool_input") or {}).get("file_path", ""))
    kind = cfg.classify(rel) if rel else None
    if not kind:
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
        from rtmlib.config import load
        cfg = load(root)
        {"pre": pre, "post": post, "stop": stop}.get(mode, lambda *_: None)(inp, cfg)
    except Exception as e:  # never break the user's tool call
        emit({"systemMessage": f"rtm hook ({mode}) error: {type(e).__name__}: {e}"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
