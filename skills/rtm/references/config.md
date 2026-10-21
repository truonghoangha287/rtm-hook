# `rtm.config.json` — schema 2 (flow of steps)

The file lives at the repo root and is created by `rtm.py init --template …`. After that it belongs
to the team: change it freely, and kit upgrades never overwrite it. Shipped templates are in
`../templates/*/flow.json`.

```jsonc
{
  "schema": 2,
  "template": {"name": "esdlc-waterfall", "version": "1.0.0"},   // provenance only
  "vars": {"spec": "specs/001-x", "code": "payment-hub"},         // {spec} usable in every path
  "rtm": {
    "index": "{spec}/01-requirements/rtm.md",   // hand sections + summary + TOC
    "dir": "{spec}/01-requirements/rtm",        // optional: one generated file per view
    "shard_size": 50,                           // optional: split big views by ID range
    "max_list": 6, "count_only": ["code"]       // cell display
  },
  "exclude": ["**/*-backup/**", "**/target/**"],
  "flow": [ /* steps, upstream first */ ],
  "coverage": [{"from": "ac", "to": "test", "severity": "P3"}],
  "status": {"initial": "Open", "lld": "Designed", "test": "Tested"},  // optional stage names
  "views": "auto",                              // or a list, or {"auto": true, "add": [...], "drop": [ids]}
  "stop_block_severities": ["P0", "P1"],
  "max_messages": 5
}
```

## A step: input → output

```jsonc
{
  "step": "lld",                       // id: lowercase, unique
  "label": "LLD",                      // column / message label
  "severity": "P1",                    // severity when the consumes rule is broken
  "produces": {                        // OUTPUT
    "ids": ["TASK"],                   //   ID prefixes this step defines (unique across the flow)
    "in": [{"files": ["{spec}/06a-technical-design/tasks.md"], "how": "table"}],
                                       //   table: ID in the first cell; refs = rest of the row
                                       //   heading: heading starts with the ID; refs = the section
    "children": {                      //   optional, heading steps only: items inside each section
      "step": "ac", "label": "AC", "suffix": "AC",
      "pattern": "^\\s*[-*]\\s*\\*\\*AC(\\d+)\\b",   // must capture the child number
      "example": "- **AC{n}:** Given … then …"       // must match the pattern (used by selftest)
    }
    // or, for code / tests:  "files": ["{code}/src/test/**/*.java"], "inherit_from": "package-info.java"
  },
  "consumes": {                        // INPUT
    "steps": ["hld", "req"],           //   upstream steps whose IDs count as this step's links
    "rule": "all",                     //   all = one of each; any = at least one (default)
    "attrs": ["source"],               //   attributes that can satisfy the rule (see attrs)
    "walk": ["req"],                   //   steps followed for forward/backward views (default = steps)
    "marker": "Verifies:"              //   files steps: only lines containing this create links
    // "require": [["hld"], ["req","@source"]]   explicit groups, overrides rule
  },
  "attrs": {"source": {"from": "index", "key_col": "BR", "value_col": "Source"}}
                                       // read a column of a table (in the index or another file)
}
```

**Validation** fails fast, with a message, on any of these:

- unknown or duplicate steps
- a prefix produced by two steps
- a consumes cycle (self-loops are allowed)
- `walk` that isn't a subset of `steps`
- a bad children `pattern`, or an `example` that doesn't match it
- unknown `{vars}`, or vars still set to their `<placeholder>`

`rtm.py flow check` also runs a **doctor** against the real repo. It flags:

- inputs that match no files
- steps that find no IDs
- markers that appear nowhere
- attribute tables that aren't found

## Views

With `"views": "auto"`, the views are derived from the flow, so editing the flow re-shapes the matrix:

| Flow feature | View |
|---|---|
| a root step (consumes no step) | `forward-<root>`: root → each later step on its walk path → status |
| a step with ≥ 2 required groups (`rule: all`) | `justify-<step>`: one column per group, ✓/✗ |
| a step with children | `coverage-<child>`: per parent, covered/total children → the target in `coverage` |
| the last step | `backward-<step>`: item → what it traces to → root → source |
| always | `summary` and `toc`, in the index |

To add or override views, use `{"auto": true, "add": [view…], "drop": ["id"]}` or a full list.

| type | keys |
|---|---|
| `forward` | `root`, `columns`, optional `prefix` |
| `justify` | `layer` |
| `children` | `parent`, `target` |
| `backward` | `layer`, `up` |
| `summary` | none |
| `toc` | none |

Each view also takes optional `title`, `file` and `shard_size`.

With `rtm.dir`, each view is written to `<dir>/<id>.md`. If it has more than `shard_size` rows, it
becomes `<dir>/<id>/<PREFIX>-001-050.md` and so on (ID-range shards, so new IDs touch one file).
Stale generated files are deleted on sync, but only files carrying the generated header.

## State (`.rtm/`)

| File | Purpose | Commit? |
|---|---|---|
| `baseline.json` | accepted findings | **commit** |
| `last.json` | findings after the last sync | ignore (in `.gitignore`) |
| `start.json` | findings before this session's first edit | ignore (in `.gitignore`) |
| `dirty` | files touched since the last clean Stop | ignore (in `.gitignore`) |
