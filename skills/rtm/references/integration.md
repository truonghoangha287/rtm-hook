# Integrating other skills with the RTM

The RTM has a single integration point: **IDs written in the agreed places** (see SKILL.md, "The
contract"). Skills never write `rtm.md`.

## Producer skills (BA, PO, SA/TL, dev, QA)

1. Emit IDs in the agreed form for your layer:
   - a table row with the ID in the first cell and its `Traces` in the same row, or
   - a heading `ID — title` with traces in that section, or
   - `TASK-###` in code Javadoc / `Verifies:` in test Javadoc.
2. As the final step, run:
   ```bash
   python3 .claude/skills/rtm/scripts/rtm.py sync
   python3 .claude/skills/rtm/scripts/rtm.py check --new --gate
   ```
   If the gate fails, fix the source artifact before handing off.
3. Gate / assemble / sign-off skills use `check --gate` **without** `--new` when the whole matrix
   must be clean.

Inside an interactive Claude Code session the hooks already do steps 2–3 automatically. The
explicit call matters for headless runs, subagents with hooks disabled, and CI.

## Consumers (dashboards, reviewers, CI)

```bash
python3 .claude/skills/rtm/scripts/rtm.py check --json
```
```json
{"pass": false, "counts": {"P0": 0, "P1": 2, "P2": 5, "P3": 40},
 "findings": [{"rule": "MISSING-UPSTREAM", "severity": "P1", "subject": "TASK-40",
               "file": "…/technical-task-breakdown.md", "line": 57,
               "msg": "TASK-040 has no HLD reference", "detail": "hld", "fingerprint": "…"}]}
```

`why <ID>` prints a single chain for humans or prompts.

## Adding a layer or changing the chain

Edit `rtm.config.json` only; no code change is needed. Examples:

- **Add a QA test-case doc between AC and code tests:** add a layer
  `{"id":"tc","prefixes":["TC"],"define":[{"files":["…/test-cases.md"],"how":"table"}],"upstream":["ac","req"],"require":[["ac","req"]]}`,
  then point the `test` layer's `upstream` at `["tc"]`.
- **Add an upstream source system:** add a layer before `br` whose IDs (`SRC-###`) are defined in an
  exported table, and give `br` `"upstream": ["src"], "require": [["src"]]`.
