# Editor corrections store

Approved expert corrections for the Klawiter dataset, as patch files consumed by
`pipeline/apply_patches.py`. This folder plus its git history is the audit trail
of the Expert-in-the-Loop curation: every correction is a tracked, reversible
change with its provenance, author role, and timestamp. Design context:
`knowledge/eil-editing.md`.

## Run order

`apply_patches.py` is a final overlay, run after `inject_provenance.py`:

```
05_to_jsonld.py  →  inject_provenance.py  →  apply_patches.py
```

The base pipeline writes machine values with `regex` / `llm` / `missing`
provenance; the overlay re-applies the corrections in this folder on top,
setting the corrected fields to provenance `editor`. Because the store is
authoritative and re-applied each run, editor values are never lost and never
silently overwritten when the base pipeline is re-run.

## Patch file format (v2)

```json
{
  "patchVersion": 2,
  "created": "2026-06-21T10:00:00Z",
  "source": "klawiter-eil-interface",
  "patches": [
    {
      "pageId": 4012,
      "field": "publisher",
      "action": "correct",
      "oldValue": "Leipzig",
      "newValue": "Insel-Verlag",
      "previousProvenance": "llm",
      "edited_by": "Editor (SZD)",
      "edited_at": "2026-06-21T10:00:00Z",
      "source": "human"
    }
  ]
}
```

- `pageId` is the entry's `sourcePageId`.
- `field` is the frontend field key (`publisher`, `location`, `translator`,
  `pageCount`, `title`, `year`, ...).
- `action` is one of `accept` (confirm a correct value), `correct` (replace a
  wrong value), `add` (fill a field the source contains but extraction missed).
- `edited_by` carries the role, not a personal name, per the data-privacy
  convention.
- `source` is `human` (editor) or `agent` (automatic verification).

Multiple corrections to the same field are kept in chronological order by
`edited_at`; the last one determines the displayed value, the full sequence
stays in the entry's `edit_history`.
