# rtm-kit

A Requirements Traceability Matrix that is **generated** from your artifacts, **checked** on every
change, and driven by a **flow you configure per project**.

```
template ──init──► rtm.config.json (flow of steps: produces → consumes)   ← the team edits this
                          │
artifacts ──scan──► trace graph ──► views ──► rtm.md (index) + rtm/*.md (sections, ID-range shards)
                          │
                          ├──► check (DANGLING · MISSING-UPSTREAM · NOT-COVERED · GEN-EDITED)
                          ├──► why / query  (answers stay small however big the project gets)
                          └──► selftest     (contract tests generated from the flow itself)
```

| Part | What it is |
|---|---|
| `skills/rtm/scripts/rtm.py` | CLI: `why`, `query`, `sync`, `check`, `baseline`, `templates`, `init`, `flow show/check/apply`, `selftest`. Stdlib only, Python 3.10+ |
| `skills/rtm/scripts/rtm_hook.py` | Claude Code hooks: Pre guards generated output · Post syncs on artifact or flow edits · Stop blocks only on *new* P0/P1 |
| `skills/rtm/templates/` | `esdlc-waterfall`, `agile`, `minimal` |
| `skills/rtm/SKILL.md` | the `/rtm` skill: query first, the artifact contract, how to change a flow |
| `examples/simple-payment/` | install command and generated preview for the SEPA Payment Hub |

## Install

```bash
./install.sh /path/to/repo --template esdlc-waterfall --set spec=specs/001-x --set code=svc --title "My system"
cd /path/to/repo
python3 .claude/skills/rtm/scripts/rtm.py flow show       # the flow, step by step
python3 .claude/skills/rtm/scripts/rtm.py flow check      # doctor: does the repo match the flow?
python3 .claude/skills/rtm/scripts/rtm.py selftest        # generated contract tests for this flow
python3 .claude/skills/rtm/scripts/rtm.py sync --diff     # preview
python3 .claude/skills/rtm/scripts/rtm.py sync && python3 .claude/skills/rtm/scripts/rtm.py baseline
```

To change the flow later, edit `rtm.config.json`. The hook validates it and re-syncs. Then run
`flow check` and `selftest`.

## Test

```bash
cd tests && python3 -m unittest -v
```

The tests have two parts:

- **`test_rtm.py`**: unit tests for the engine and the hooks.
- **`test_flows.py`**: the generated contract suite, run over every template and two custom flows.
  It also checks that the suite *fails* when the engine is broken or a flow is invalid.

Docs: [config / flow schema](skills/rtm/references/config.md) · [integration](skills/rtm/references/integration.md)
