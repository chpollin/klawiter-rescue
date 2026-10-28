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
updated: 2026-10-28
---

# Handoff

This process inbox holds only open handoff points, the results that arrived from agents, sessions or research and still wait to be checked, integrated or rejected. Before using a point, check its source and its current target. Integrate durable content into the responsible document, record subject, source, target and result or the reason for rejection briefly in [Journal](journal.md), and then remove the point completely. Accepted future work goes into [Plan](plan.md).

## Open handoff points

### Comments in the AI operator's paths renamed

- Received: 2026-10-28
- Source: unification of the knowledge along the Promptotyping templates (journal entry of 2026-10-28)
- Target: the paused AI operator, paths `docs/js/` and `pipeline/print_volumes/viewer/cards.js` ([Governance](governance.md#paths))
- Context: the comments of `docs/js/edit.js`, `docs/js/home.js` and `cards.js` name the renamed documents `frontend-architecture.md`, `governance.md` and `design.md`; no code changed. The AI operator was paused, so the research coordinator made the change.
- Next action: when the operator assigns the AI operator again, it takes the renamed references into its working state, and the point leaves this inbox with a journal record.

### UI review and work package of 2026-10-24

- Received: 2026-10-24
- Source: workflow run wf_236f71c6-273, agents understand:uxreview and draft:ui-package
- Target: [Plan](plan.md), increments of the record desk; [Design](design.md)
- Context: the package was written for the AI operator, whom the operator has since paused; the research coordinator builds the interface. Its items overlap with increment 1, which is running.
- Next action: after increment 1 is committed, merge the remaining items into increments 2 to 5 of the plan.

### Identifier and citation practice

- Received: 2026-10-24
- Source: research agent on GW, ISTC, VD16 to VD18, ESTC, RISM, the Köchel catalogue online, Darwin Online, and persistent identifier practice
- Target: [Merged bibliography](print-wiki-merge.md), Record model; [Plan](plan.md), M2 Identifiers
- Context: RISM is the closest precedent (its own identifier first, the printed catalogue numbers as cited references that can name several records); the recommendation is an opaque group identifier under a host-independent namespace, aliases that resolve to source records, redirects on joins and successor pages on splits, and a dataset DOI per release.
- Operator point: the identifier scheme is the operator's decision.
