---
name: br-to-testcase
description: Sample QA skill — generate test cases (TC-###) from business requirements (BR-###). Use when asked to "generate test cases from BR", "write TCs for the BRD", or to exercise the RTM hook with a producer skill.
---

# BR → Test case (sample)

A deliberately small producer skill. Its only job is to write `TC-###` rows that cite a `BR-###`,
so the RTM hooks have something to sync and check.

## Steps

1. Find the files from the flow (don't hardcode paths):
   ```bash
   python3 .claude/skills/rtm/scripts/rtm.py flow show
   ```
   - BR file: the `from` of the `br` step
   - TC file: the `from` of the `tc` step (if there is no `tc` step, stop and tell the user)
2. Read the BR table and the existing TC table. Skip BRs that already have a TC.
3. For each remaining BR, add 1–2 rows to the TC table — one happy path, plus one negative/boundary
   case if the BR has a rule or threshold. Keep scenarios one line.
   ```markdown
   | TC | Scenario | Expected | Requirement |
   |---|---|---|---|
   | TC-005 | Change an order's quantity | Audit row holds user, timestamp and old/new value | BR-004 |
   ```
   - TC IDs continue from the highest existing number
   - the ID goes in the first cell, the BR ID in the `Requirement` cell
4. Finish with the gate (the hooks already do this in interactive sessions):
   ```bash
   python3 .claude/skills/rtm/scripts/rtm.py sync
   python3 .claude/skills/rtm/scripts/rtm.py check --new --gate
   ```
   If the gate fails, fix the TC rows — never edit `rtm.md` or `rtm/`.
