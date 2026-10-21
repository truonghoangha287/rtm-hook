# simple-payment (SEPA Payment Hub)

Install with the `esdlc-waterfall` template:

```bash
./install.sh /Users/frozenman/simple-payment --template esdlc-waterfall \
  --set spec=specs/001-bank-payment-system --set code=payment-hub --title "SEPA Payment Hub"
```

`preview/` is what `rtm.py sync` produces on a copy of the repo:

- `rtm.md`: the index, which replaces `specs/001-bank-payment-system/01-requirements/rtm.md`. It
  keeps the hand-written sections (header, Source → BR, Regulatory, Methodology) and adds the
  generated summary and table of contents.
- `rtm/*.md`: one generated file per view.

What the matrix shows at adoption:

- 0 dangling IDs.
- Every FR/NFR, story, HLD item and TASK carries its required links.
- 107 test classes still need a `Verifies:` line.
- 41 code files cite no TASK.
- No BR or AC is reached by a test yet.

These 314 findings are recorded with `rtm.py baseline` as known debt.
