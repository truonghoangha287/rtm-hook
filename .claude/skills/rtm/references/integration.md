# Integrating other skills with the RTM

The integration point is the **flow**: each step declares the artifact it reads (`produces.in` /
`files`) and the references it requires (`consumes`). Skills never write the matrix files.

## Producer skills (BA, PO, SA/TL, dev, QA)

1. Find out what your step expects: `python3 .claude/skills/rtm/scripts/rtm.py flow show`.
2. Write IDs in that form:
   - table steps: the ID in the first cell, upstream IDs in the same row
   - heading steps: `ID — title`, with upstream IDs in the section
   - files steps: a mention, or a `marker` line
3. As the final step, run:
   ```bash
   python3 .claude/skills/rtm/scripts/rtm.py sync
   python3 .claude/skills/rtm/scripts/rtm.py check --new --gate
   ```
   If the gate fails, fix the artifact before handing off. Gate / sign-off skills drop `--new`.

In interactive Claude Code sessions the hooks already do step 3. The explicit call matters for
headless runs, subagents and CI.

## Adding your skill's output as a new step

Add a step to `rtm.config.json` (example: a QA test-case document between AC and code tests):

```jsonc
{"step": "tc", "label": "Test case", "severity": "P1",
 "produces": {"ids": ["TC"], "in": [{"files": ["{spec}/09-test-plan/test-cases.md"], "how": "table"}]},
 "consumes": {"steps": ["ac", "req"], "rule": "any"}}
```

Then put `"tc"` into the downstream test step's `consumes.steps`, and run `rtm.py flow check` and
`rtm.py selftest`. The views (forward column, coverage) pick up the new step automatically.

## Consumers (dashboards, reviewers, CI)

```bash
python3 .claude/skills/rtm/scripts/rtm.py check --json          # {pass, counts, findings[…]}
python3 .claude/skills/rtm/scripts/rtm.py query gaps --step ac --to test --json --limit 0
python3 .claude/skills/rtm/scripts/rtm.py selftest --json       # does the flow itself still hold?
```

Each finding looks like this:

```json
{"rule": "MISSING-UPSTREAM", "severity": "P1", "subject": "TASK-40", "file": "…", "line": 57,
 "msg": "TASK-040 has no HLD reference", "detail": "hld", "fingerprint": "…"}
```
