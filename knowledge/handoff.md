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

### Data reach audit of 2026-10-24

- Received: 2026-10-24
- Source: workflow run wf_236f71c6-273, agent understand:reach
- Target: [Data](data.md), [Plan](plan.md), M1 wiki data
- Context: every record reaches the frontend projection, but the card's coverage rested on hidden markers (now corrected in the test); a value emptied by the binding rule shows the provenance `missing` like a source gap; 77 publishers and 29 places differ between the edition graph and the publication layer on linked editions; 22 edition nodes of page 3757 reach no publication; between 67 and 105 redirect aliases are missing in the frontend redirect map and 71 redirect targets are dropped without a claim; 13 category pages with text reach no card.
- Next action: verify each finding against the current outputs, turn the confirmed ones into M1 items or data.md statements; the rule gap belongs to the planned distinction of gap kinds.

### UI review and work package of 2026-10-24

- Received: 2026-10-24
- Source: workflow run wf_236f71c6-273, agents understand:uxreview and draft:ui-package
- Target: [Plan](plan.md), increments of the record desk; [Design](design.md)
- Context: the package was written for the AI operator, whom the operator has since paused; the research coordinator builds the interface. Its items overlap with increment 1, which is running.
- Next action: after increment 1 is committed, merge the remaining items into increments 2 to 5 of the plan.

### Conventions of the print volumes

- Received: 2026-10-24
- Source: read-only research agent over the local volumes, report in the session
- Target: [Print volumes](print-volumes.md), Open questions and Abbreviations and sigla; [Merged bibliography](print-wiki-merge.md), Open questions
- Context: the star after an address marks an excerpt, shown by the compiler restating the same list with the abbreviation for excerpt in Addendum I; D 224 to D 227 of 1991 were absorbed into D 88a, D 98, D 154 and D 159 of the revised file; the "I," in trade citations names the main volume, while "I 83" without a comma is an address in section I; the unresolved periodical sigla are three single-use near-variants, and the informant residue is listed per volume.
- Blocker: the print rebuild agent is editing `print-volumes.md`.
- Next action: integrate once the print rebuild is committed, paraphrased with PDF pages and without print text.

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
