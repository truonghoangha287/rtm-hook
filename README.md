# rtm-kit

A generated, self-checking Requirements Traceability Matrix for Claude Code projects.

```
Source → BR → FR/NFR → HLD → LLD → Code → Test          (LLD must cite HLD and a requirement)
                  └─→ Story → AC ───────────→ Test        (tests declare `Verifies: STORY-x/ACn | BR-x`)
```

- **`skills/rtm/scripts/rtm.py`**: a stdlib-only Python 3.10+ CLI with `sync`, `check`, `why`, `baseline` and `stats`.
- **`skills/rtm/scripts/rtm_hook.py`**: Claude Code hooks:
  - **Pre:** protects the generated blocks.
  - **Post:** syncs after a doc edit; marks code and test edits dirty.
  - **Stop:** syncs once per turn and blocks only on *new* P0/P1 findings.
- **`skills/rtm/SKILL.md`**: the `/rtm` skill and the contract that other skills follow.
- **`examples/simple-payment/rtm.config.json`**: the full config for the SEPA Payment Hub repo.

## Install

```bash
./install.sh /path/to/repo --config examples/simple-payment/rtm.config.json
cd /path/to/repo
python3 .claude/skills/rtm/scripts/rtm.py sync --diff     # preview
python3 .claude/skills/rtm/scripts/rtm.py sync
python3 .claude/skills/rtm/scripts/rtm.py baseline       # accept existing debt
```

## Test

```bash
cd tests && python3 -m unittest -v
```

Docs: [config reference](skills/rtm/references/config.md) · [integration contract](skills/rtm/references/integration.md)
