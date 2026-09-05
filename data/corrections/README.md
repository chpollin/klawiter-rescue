# Released correction store

Place reviewed curation export documents here as JSON files. The files and their Git history are the released decision record. The browser stores a local editing session and exports a document; importing that document into this directory is a separate repository change. The [frontend contract](../../knowledge/frontend.md) explains the interface, and [data contracts](../../knowledge/data.md) explain provenance and review states.

## Field corrections

The interface exports `patchVersion: 2` with a `patches` array. This illustrative shape is not a released bibliographic decision:

```json
{
  "patchVersion": 2,
  "created": "2026-09-05T12:00:00Z",
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
      "edited_at": "2026-09-05T12:00:00Z",
      "source": "human"
    }
  ]
}
```

[apply_patches.py](../../pipeline/apply_patches.py) requires an object with `patchVersion: 2` and a `patches` array. A document containing only `reconciliationPatchVersion: 1` and a `reconciliationPatches` array contributes no field patches. Missing or malformed collections and unsupported field versions are rejected. Its record validator requires:

- `pageId`: a positive integer, excluding booleans and numeric strings; the ID must resolve to a frontend entry before the batch can be written.
- `field`: `publisher`, `location`, `translator`, or `pageCount`.
- `action`: `accept`, `correct`, or `add`.
- `source`: `human` or `agent`.
- `edited_by` and `edited_at`: present on every record; `edited_at` must parse as an ISO-8601 timestamp with a timezone, such as `Z` or `+02:00`.
- For `add`, `oldValue` must be empty. For `correct`, `newValue` must be nonempty and differ from `oldValue`.

The field validator does not require a separate evidence field or verify a value's bibliographic meaning. Source review remains a release responsibility.

Records are replayed in timestamp order, comparing actual instants across timezone offsets. Equal timestamps retain file/array load order. `correct` and `add` assign `newValue`; `accept` confirms the existing value. Replay rebuilds `edit_history`, sets field provenance to `editor`, and updates entry review status while preserving existing field-level review records. A corrected location retains or receives `locationSameAs` only where the reviewed link layer supports the resulting location.

`oldValue` drift is a warning, not an application guard. If the current value matches neither `oldValue` nor `newValue`, the mismatch is recorded, but the released store remains authoritative and replay proceeds. Matching `newValue` is treated as an already-applied patch. Review drift in `data/output/corrections-report.json`.

If any parsed patch record is invalid or any target ID is unknown, the command writes its report and exits nonzero before writing the frontend dataset. Other valid records in that batch are not persisted. This is a file-write boundary; the helper may already have changed its in-memory entries while producing the report.

The frontend input must contain a nonempty `entries` array. Malformed envelopes or frontend inputs fail before replay and may produce no new corrections report.

The normal pipeline applies field corrections after provenance projection and triage. To replay against an existing frontend build:

```bash
python -m uv run python pipeline/apply_patches.py
```

Field replay overlays `docs/data/klawiter.json`. Earlier CSV stages and the canonical JSON-LD are not rewritten by this command. Use the [complete pipeline](../../pipeline/README.md) and its validators for integration; field-overlay consistency across all publication formats remains a separate contract.

## Reconciliation decisions

A reconciliation export uses `reconciliationPatchVersion: 1` and a `reconciliationPatches` array. A combined document may contain both patch arrays. [lib/reconciliation.py](../../pipeline/lib/reconciliation.py) loads these decisions during the Gate-2 rebuild, before publication links are produced.

| Record field | Contract |
|---|---|
| `entityType` | `location`, `work`, `person`, or `publisher` |
| Subject | `subjectId` for a work; `subject` for the other kinds |
| Target | `szdId` for a work; `qid` for a Wikidata entity |
| Action | `confirm`, `correct`, `reject`, or `unresolved` |
| Decision record | `decisionId`, `decidedBy`, `decidedAt`, and source-backed `evidence` |

The loader checks the reconciliation envelope version, entity kind and required keys. The build validates decision subjects, actions, evidence and candidate targets. Use timezone-bearing timestamps in exported decisions; the field replay's timestamp ordering and validation are not a promise of equivalent reconciliation timestamp validation. Reconciliation replacement follows file/array load order, preserving the prior decision in `supersedes` and `supersedesDecisionId`.

Only evidence-bearing `confirm` and `correct` decisions produce publishable links. `reject` leaves the subject without an accepted link. `unresolved` preserves an open source-bound claim and competing interpretations. These decisions require a Gate-2 rebuild and final projection validation; a field-overlay-only command does not apply them.
