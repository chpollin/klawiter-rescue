---
title: Handoff
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: active
language: en
created: 2026-10-24
updated: 2026-10-30
---

# Handoff

This process inbox holds only open handoff points, the results that arrived from agents, sessions or research and still wait to be checked, integrated or rejected. Before using a point, check its source and its current target. Integrate durable content into the responsible document, record the transition briefly in a new entry at the top of [Journal](journal.md), and then remove the point completely. Accepted future work goes into [Plan](plan.md).

## Open handoff points

### Session of 2026-10-30: open questions, running audits, drafts

- Received: 2026-10-30
- Source: the guided session of 2026-10-30 (journal entries of that day)
- Target: [Plan](plan.md), Program from 2026-10-30
- Context: The operator's open questions stand as decisions E1 to E8 in the acceptance view (`pipeline/acceptance.py`, ACCEPTANCE), each with reason, recommendation and sample page. The read-only audit of the pipeline's test and validation profile arrived: the checks are strong on whole records and weak on which passage a value comes from and which state it carries; of 13 faults injected into a copy, 9 passed all targeted tests (a value from another publication's block, a wrong value behind a `repeated` gap or a `normalised` derivation, a producer swapped from rule to model, a dropped publication, a zeroed slice hash, a reversed order, and the first TEI export's flattened producer and state). Its notes and harness lie in the session scratchpad (`audit-pipeline/`). Drafts for the Promptotyping case study and chapter 3 and for the DIA-XAI proposal (RQ3 to RQ5) and an observation log of the session also lie there and await the operator's acceptance as statement lists.
- Next action: record the operator's answers in `pipeline/data/acceptance-decisions.json` and carry them into [TEI profile](tei-profile.md); integrate the audit's smallest checks (zone of a publication value, honesty of gaps and derivations, provenance against the frozen cache, editions to publications, slice and occurrence hashes, the CI cache key) into the test suite.

### Audit of the GAMS and Stefan Zweig Digital requirements, 2026-10-30

- Received: 2026-10-30
- Source: read-only agent over the repositories `SZD-split` (branch `gams-www-split`, the current knowledge of the presentation layer), `ZIMLAB/szd` at 499a28a, the vault and the public GAMS documentation; GAMS read only by GET on public data streams
- Target: [Plan](plan.md), D1 and D3; [TEI profile](tei-profile.md)
- Context: The local `SZD` master has diverged from origin (three commits ahead, three behind), so line references hold for `SZD-split`. Findings, with their kind of evidence:
  - GAMS validates against TEI P5 at ingest and fails an invalid file (documented); how strictly is open, because two productive konvolut files are invalid against tei_all 4.12.0. The sample breaks only at `application/@version`; a version number belongs there and the timestamp in `@when`.
  - The PID stands once in `fileDesc/publicationStmt/idno[@type='PID']` (met); `o:szd.klawiter` is free on production (404 on 2026-10-30), staging unchecked without VPN.
  - A new object under `cirilo:TEI.szd` inherits the generic stylesheet; the operator sets `STYLESHEET` and `TORDF` in Cirilo after the ingest.
  - No stylesheet of `gams-www` knows `biblStruct`; a page stylesheet includes `szd-static.xsl` and `szd-Templates.xsl`, defines `content`, and needs branches in the PID switches of `szd-Templates.xsl`; visible labels are i18n keys of a server catalogue in no repository. The menu links externally to `klawiter.stefanzweig.digital` (`szd-static.xsl:434`).
  - `szd-TORDF.xsl:73-121` switches on the PID; an unknown PID writes "No data source define!" into `rdf:RDF` (code; effect on ingest unverified). Search needs a `FROM <o:szd.klawiter>` line in each query template and an entry in `SearchCollections` of `szd-Suche.xsl`.
  - The Dublin Core mapping of `cirilo:szd` takes `//t:teiHeader//t:title[1]`, which would collect every source title in `sourceDesc`, and `date` and `author` from the header (inferred from the live mapping): the source entries belong outside the header, which also takes the print records out of `sourceDesc`.
  - `SZD/scripts/check_data.py` passes the sample without a finding; the staging package builder and `local-test-build/gams-objects.toml` do not list Klawiter; the ingest folder must hold the TEI file only, never anything from `data/print/`.
  - Identifiers become permalinks and RDF URIs, so the identifier scheme must stand before an ingest beyond staging.
- Next action: take the automatable checks (tei_all, single PID, `check_data.py`, a Dublin Core simulation, identifier register, package hygiene) into D1 and D3; ask the operator about the strictness of validation in GAMS, the RDF branch for search, the menu link and the i18n keys.

### Identifier and citation practice

- Received: 2026-10-24
- Source: research agent on GW, ISTC, VD16 to VD18, ESTC, RISM, the Köchel catalogue online, Darwin Online, and persistent identifier practice
- Target: [Merged bibliography](print-wiki-merge.md), Record model; [Plan](plan.md), M2 Identifiers
- Context: RISM is the closest precedent (its own identifier first, the printed catalogue numbers as cited references that can name several records); the recommendation is an opaque group identifier under a host-independent namespace, aliases that resolve to source records, redirects on joins and successor pages on splits, and a dataset DOI per release.
- Operator point: the identifier scheme is the operator's decision.
