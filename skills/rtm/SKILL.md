---
name: rtm
description: Keep the Requirements Traceability Matrix (rtm.md) in sync and verified — Source → BR → FR/NFR → HLD → LLD → Code → Test, with story ACs → Test. Use when the user asks to update/sync/check the RTM or traceability, asks "what traces to X" / "why does X exist", when an RTM hook reports findings, or when a skill that produces BRs, stories, HLD, LLD, code or tests finishes and needs its links recorded.
---

# RTM — traceability matrix, generated and checked

The matrix is **generated** from IDs already written in the artifacts by a deterministic script
(`scripts/rtm.py`). You never type rows into `rtm.md`. You fix traceability **in the source
artifact**, and the script and hooks rebuild the matrix.

Project wiring lives in `<repo>/rtm.config.json` (layers, files, rules, blocks); schema in
[references/config.md](references/config.md).

## Commands

Run from the repo root (`S=.claude/skills/rtm/scripts`):

| Goal | Command |
|---|---|
| Rebuild generated blocks | `python3 $S/rtm.py sync` (`--diff` to preview, writes nothing) |
| List problems | `python3 $S/rtm.py check` · `--new` (hide baseline) · `--file PATH` · `--json` |
| Gate (CI / sign-off) | `python3 $S/rtm.py check --gate` → exit 1 on any P0/P1 |
| Explain one item | `python3 $S/rtm.py why BR-004` (or a TASK, AC `STORY-005/AC2`, or a file path) |
| Accept current debt | `python3 $S/rtm.py baseline` — only when the user asks |
| Counts per layer | `python3 $S/rtm.py stats` |

Prefer `check --new --limit 20` over reading `rtm.md`. The file is large and the CLI already
has the answer.

## How to write traceable artifacts (the contract)

Each layer is recognised by where its ID is defined and which IDs sit next to it:

- **Table-defined** (BRD, NFR spec, HLD registries, LLD task breakdown): the ID is in the **first
  cell** of a table row, and the upstream IDs go in the **same row** (e.g. a `Traces` column).
  Compressed lists are fine: `FR-009/010 · CMP-005 · ADR-05/15`.
- **Heading-defined** (FRD, stories, ADRs, sequences): the heading starts with the ID. Upstream IDs
  go in the heading or that section's body, e.g. `### FR-006 — VoP *(traces: BR-004)*`.
- **LLD** must cite **both** an HLD element (CMP/ADR/INT/SD) **and** a requirement (FR/NFR).
- **Code**: the class Javadoc or `package-info.java` names its `TASK-###`.
- **Tests**: the class Javadoc carries a `Verifies:` line naming story ACs and/or BRs:
  ```java
  /**
   * TASK-014 money-path tests.
   * Verifies: STORY-011/AC1, STORY-011/AC3, BR-008
   */
  ```
- **Source of a BR**: the hand-maintained `Source → BR` table in `rtm.md` (outside the generated
  markers).

## Handling findings

| Rule | Meaning | Fix (in the source artifact) |
|---|---|---|
| `DANGLING` P0 | cites an ID that is not defined anywhere | correct the typo, or define the ID upstream |
| `MISSING-UPSTREAM` | the node lacks a required link (e.g. TASK without HLD, test without `Verifies:`) | add the missing ID to the row, section or Javadoc |
| `NOT-COVERED` | BR or AC has no test yet | add a test with `Verifies:`, or leave it (progress signal) |
| `GEN-EDITED` P1 | someone hand-edited a generated block | revert it; change the source, then `sync` |

Don't invent links to silence a finding. If no honest upstream exists, tell the user. The gap may
be real: a missing requirement, or gold-plated code.

## Hooks (installed by `install.sh`)

- **PreToolUse**: blocks edits inside `<!-- rtm:begin … -->` blocks of `rtm.md`.
- **PostToolUse**:
  - after an edit to a requirements or design doc: syncs immediately and reports *new* findings
  - after a code or test edit: marks the file dirty
- **Stop**: if anything is dirty, syncs once, and blocks the end of the turn **only** on new P0/P1
  introduced this session (baseline debt is ignored). Fix them, or explain to the user why
  they're intended.

## For other skills

A producing skill's last step should be:
`python3 .claude/skills/rtm/scripts/rtm.py sync && python3 .claude/skills/rtm/scripts/rtm.py check --new --gate`.
Machine consumers read `check --json` → `{pass, counts, findings[{rule, severity, subject, file,
line, msg, fingerprint}]}`. See [references/integration.md](references/integration.md).
