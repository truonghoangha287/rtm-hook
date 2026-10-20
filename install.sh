#!/usr/bin/env bash
# Install the rtm skill + hooks into a repo.
#   ./install.sh <repo> [--config <rtm.config.json>] [--yes] [--dry-run]
# - symlinks <repo>/.claude/skills/rtm -> this kit's skills/rtm
# - copies --config to <repo>/rtm.config.json if the repo has none
# - merges 3 hook entries into <repo>/.claude/settings.json (shows the diff, asks first)
# - adds .rtm state files to <repo>/.gitignore
set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="" CONFIG="" YES=0 DRY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --yes) YES=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) REPO="$1"; shift ;;
  esac
done
[[ -n "$REPO" && -d "$REPO" ]] || { echo "usage: $0 <repo> [--config FILE] [--yes] [--dry-run]" >&2; exit 2; }
REPO="$(cd "$REPO" && pwd)"

run() { if [[ $DRY == 1 ]]; then echo "[dry-run] $*"; else "$@"; fi; }

# 1. skill symlink
run mkdir -p "$REPO/.claude/skills"
run ln -sfn "$KIT/skills/rtm" "$REPO/.claude/skills/rtm"
echo "skill: $REPO/.claude/skills/rtm -> $KIT/skills/rtm"

# 2. config
if [[ -f "$REPO/rtm.config.json" ]]; then
  echo "config: keeping existing $REPO/rtm.config.json"
elif [[ -n "$CONFIG" ]]; then
  run cp "$CONFIG" "$REPO/rtm.config.json"; echo "config: copied $CONFIG"
else
  echo "config: none — create $REPO/rtm.config.json (see skills/rtm/references/config.md); hooks stay no-ops until then"
fi

# 3. hooks
python3 - "$REPO/.claude/settings.json" "$YES" "$DRY" <<'PY'
import difflib, json, sys
from pathlib import Path
path, yes, dry = Path(sys.argv[1]), sys.argv[2] == "1", sys.argv[3] == "1"
cmd = 'python3 "$CLAUDE_PROJECT_DIR"/.claude/skills/rtm/scripts/rtm_hook.py '
want = {
    "PreToolUse": ("Write|Edit|MultiEdit", cmd + "pre"),
    "PostToolUse": ("Write|Edit|MultiEdit", cmd + "post"),
    "Stop": (None, cmd + "stop"),
}
before = path.read_text() if path.exists() else "{}\n"
data = json.loads(before)
hooks = data.setdefault("hooks", {})
for event, (matcher, command) in want.items():
    entries = hooks.setdefault(event, [])
    if any(h.get("command") == command for e in entries for h in e.get("hooks", [])):
        continue
    entry = {"hooks": [{"type": "command", "command": command, "timeout": 30}]}
    if matcher:
        entry = {"matcher": matcher, **entry}
    entries.append(entry)
after = json.dumps(data, indent=2) + "\n"
if after == before:
    print("hooks: already installed"); sys.exit(0)
sys.stdout.writelines(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                           str(path), str(path) + " (new)"))
if dry:
    print("[dry-run] settings.json not written"); sys.exit(0)
if not yes:
    if input("Write these hook entries? [y/N] ").strip().lower() != "y":
        print("hooks: skipped"); sys.exit(0)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(after)
print(f"hooks: written to {path}")
PY

# 4. gitignore
GI="$REPO/.gitignore"
if ! grep -qs '^\.rtm/dirty$' "$GI"; then
  if [[ $DRY == 1 ]]; then echo "[dry-run] append .rtm state ignores to $GI"
  else printf '\n# rtm hook state (keep .rtm/baseline.json committed)\n.rtm/dirty\n.rtm/last.json\n.rtm/start.json\n' >> "$GI"; echo "gitignore: updated"; fi
fi

echo
echo "next: cd \"$REPO\" && python3 .claude/skills/rtm/scripts/rtm.py sync --diff   # preview"
echo "      python3 .claude/skills/rtm/scripts/rtm.py sync && python3 .claude/skills/rtm/scripts/rtm.py baseline"
