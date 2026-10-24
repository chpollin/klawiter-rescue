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
updated: 2026-10-24
---

# Handoff

This process inbox holds only open handoff points, the results that arrived from agents, sessions or research and still wait to be checked, integrated or rejected. Before using a point, check its source and its current target. Integrate durable content into the responsible document, record subject, source, target and result or the reason for rejection briefly in [Journal](journal.md), and then remove the point completely. Accepted future work goes into [Plan](plan.md).

## Open handoff points

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

### Two findings of the retired lab

- Received: 2026-10-24
- Source: report of the AI operator on the lab, recorded before the lab was retired
- Target: [Data](data.md), [Testing](testing.md)
- Context: the production label omitted that no person decided, which the wiki batch of 71a0fe0 has since changed; some flat translator values carry a double space that no exact source occurrence matches.
- Next action: verify the double space against the current data and fix it at its root or reject the finding.
