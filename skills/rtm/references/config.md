# `rtm.config.json` reference

Lives at the repo root. All paths are POSIX paths relative to that root. Globs support `*`, `?`
and `**/`. A full real example is `examples/simple-payment/rtm.config.json`.

```jsonc
{
  "rtm": "specs/…/rtm.md",                // the matrix file (generated blocks + hand sections)
  "exclude": ["**/*-backup/**", "**/target/**"],
  "layers": [ … ],                         // chain order = display order
  "coverage": [{"from": "br", "to": "test", "severity": "P3"}],
  "stop_block_severities": ["P0", "P1"],   // what the Stop hook blocks on (new findings only)
  "max_messages": 5,                       // findings per hook message
  "render": { … }
}
```

## Layers

| Key | Meaning |
|---|---|
| `id`, `label` | internal id / column label |
| `kind` | `"ids"` (default; IDs defined in docs) or `"files"` (one node per file: code, tests) |
| `prefixes` | ID prefixes owned by this layer, e.g. `["FR","NFR"]` |
| `define` | `[{"files": [...], "how": "table"\|"heading"}]`: where IDs are defined (`ids` kind) |
| `files` | globs (`files` kind) |
| `upstream` | layers whose IDs, when cited by this node, count as its upstream links |
| `trace_via` | subset of `upstream` used to walk the chain (default = `upstream`). Example: LLD cites HLD and FR, but walks via FR, so a BR doesn't fan out to every task of a shared component. |
| `require` | list of groups; each group needs ≥ 1 link. `[["hld"],["req"]]` = both; `[["ac","br"]]` = either. `"@source"` = the node has a `source` attribute. |
| `severity` | severity of `MISSING-UPSTREAM` for this layer |
| `attrs` | `[{"name","file","key_col","value_col"}]`: read a column from a table as a node attribute (`source`). Generated blocks are never read back. |
| `children` | `{"id","label","suffix","pattern"}`: child items inside a heading-defined section, e.g. ACs in a story. `pattern` must capture the number. Referenced as `STORY-001/AC4` or `STORY-001 AC4`. |
| `ref_marker` | `files` kind: only lines containing this text create upstream links (e.g. `"Verifies:"`); other mentions are still checked for dangling IDs |
| `inherit_from` | `files` kind: a file with no links inherits them from this sibling (e.g. `package-info.java`) |

## Render blocks

`render.blocks[]`. Each block has `id`, `type` and `title` (the heading used when it's first appended).

| type | keys | Output |
|---|---|---|
| `forward` | `root`, `columns`, optional `prefix` | one row per root node: source, downstream nodes per column, status |
| `justify` | `layer` | one row per node: one column per `require` group, ✓/✗ |
| `children` | `parent`, `target` | per parent (story): covered/total children (AC), uncovered, targets |
| `backward` | `layer`, `up` | per node with links: direct links, ancestors in `up`, source |
| `summary` | — | requirement and coverage counts plus findings by severity |

`render.stages` maps column layer → status label. Status is the furthest stage reached **without a
gap**. `count_only` lists layers shown as "N files". `max_list` caps the names per cell.

Blocks missing from `rtm.md` are appended (with their title) on the next `sync`. Move them where you
like afterwards: only the marker pair matters.

## State (`.rtm/`)

`baseline.json` (commit it), `last.json`, `start.json`, `dirty` (ignore these). See
`scripts/rtmlib/state.py`.
