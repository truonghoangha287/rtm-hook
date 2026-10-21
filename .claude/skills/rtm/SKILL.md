---
name: rtm
description: Requirements Traceability Matrix generated from the project's artifacts along a configurable flow (e.g. Source → BR → FR/NFR → Story/AC → HLD → LLD → Code → Test). Use to answer traceability questions ("what traces to BR-004", "which ACs have no test"), to update/sync/check the RTM, to act on RTM hook findings, to set up or change the traceability flow/template for a project, or when a skill producing requirements, stories, design, code or tests finishes and needs its links verified.
---

# RTM — generated, checked, flow-driven

A deterministic script (`scripts/rtm.py`) reads the IDs already written in the artifacts, builds
the trace graph along the project's **flow** (`<repo>/rtm.config.json`), writes the matrix, and
checks it. You never type rows into the matrix. Traceability is fixed **in the source artifact**.

`S=.claude/skills/rtm/scripts` (run from the repo root).

## 1. Answer questions by query (never read the matrix files)

The matrix files are large and only exist for humans to read. The graph answers directly, and the
answer stays small:

| Question | Command |
|---|---|
| What does X trace to, up and down? | `python3 $S/rtm.py why BR-004` (also a TASK, `STORY-5/AC2`, or a file path) |
| Which items of a step have nothing downstream in another? | `python3 $S/rtm.py query gaps --step ac --to test` |
| Which items break their step's rule? | `python3 $S/rtm.py query missing --step lld` |
| Find items | `python3 $S/rtm.py query list --step hld --grep ledger` |
| Counts | `python3 $S/rtm.py stats` |
| What is the flow? | `python3 $S/rtm.py flow show` |

All of these accept `--limit N`; the query commands also take `--json`.

## 2. Keep it correct

| Goal | Command |
|---|---|
| Rebuild the generated sections | `python3 $S/rtm.py sync` (`--diff` previews and writes nothing) |
| List problems | `python3 $S/rtm.py check --new --limit 20` (`--file PATH`, `--json`) |
| Gate (CI / sign-off) | `python3 $S/rtm.py check --gate` exits 1 on any P0/P1 |
| Accept current debt | `python3 $S/rtm.py baseline` (**only when the user agrees**) |

| Finding | Meaning | Fix (in the source artifact) |
|---|---|---|
| `DANGLING` P0 | cites an ID that is defined nowhere | fix the typo, or define the ID upstream |
| `MISSING-UPSTREAM` | the item breaks its step's `consumes` rule | add the missing reference to its row, section, or marker line |
| `NOT-COVERED` | nothing downstream yet in a `coverage` target | add the downstream item, or leave it (progress signal) |
| `GEN-EDITED` P1 | a generated block was hand-edited | change the source, then `sync` |

Never invent a link just to silence a finding. If there is no honest upstream, tell the user: the
gap may be real.

## 3. How artifacts must be written (the contract)

`rtm.py flow show` prints, for each step, what it **outputs** (ID prefix, defined in which file and
how) and what **input** it must cite. General rules:

- **table** step: the ID is in the **first cell** of a row, and its upstream IDs are in the same
  row. Compressed lists are fine (`FR-009/010 · CMP-005`, `FR-001..013`).
- **heading** step: the heading starts with the ID, and its upstream IDs go in the heading or the
  section body. Children (e.g. ACs) are lines in the section matching the step's pattern, and are
  cited as `STORY-001/AC4`.
- **files** step (code, tests): mention the upstream IDs in the file. If the step has a `marker`
  (e.g. `Verifies:`), only lines containing the marker count:
  `* Verifies: STORY-011/AC1, BR-008`.
- `rule: all` means one reference to **each** consumed step; `any` means at least one.

## 4. Set up or change the flow

- **New project:**
  1. `python3 $S/rtm.py templates`, then pick the closest flow.
  2. `python3 $S/rtm.py init --template <t> --set var=value … --title "<name>"`.
  3. Read the repo's real artifacts and adjust `rtm.config.json` (paths, prefixes, `how`, children
     pattern, `marker`). The schema is in [references/config.md](references/config.md).
- **Change a flow** (add, remove or reorder steps, change inputs or outputs): edit
  `rtm.config.json`. The hook validates it and re-syncs, and the views re-shape automatically. Then:
  1. `python3 $S/rtm.py flow check` (doctor: files that don't exist, steps that find nothing)
  2. `python3 $S/rtm.py selftest`: the generated contract tests for *this* flow must all pass
  3. `python3 $S/rtm.py check --new`: show the user the new findings; `baseline` only if they accept
- Never weaken a step's rule just to make findings disappear without the user saying so.

## 5. Hooks (installed by `install.sh`)

- **PreToolUse**: refuses edits to generated section files and to generated blocks in the index.
- **PostToolUse**:
  - step doc edited: sync, and report *new* findings
  - code or test edited: mark the file dirty
  - `rtm.config.json` edited: validate and re-sync. Findings caused by the flow change are not
    blamed on later edits.
- **Stop**: syncs once if anything is dirty. It blocks the end of the turn **only** on new P0/P1
  findings from this session. Fix them, or explain to the user why they're intended.

Other skills: see [references/integration.md](references/integration.md).
