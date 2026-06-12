---
title: Handoff
tags: [process, transient]
updated: 2026-06-12
---

# Handoff-Notiz (Stand 2026-06-12, Session 16)

Transiente Prozessnotiz fuer den Wiedereinstieg einer frischen Instanz. Wird beim naechsten Handoff ueberschrieben. Projektdoku liegt in den uebrigen knowledge/-Dokumenten, Verlauf im [[journal]].

## Aktueller Stand

Session 16 ist abgeschlossen und vollstaendig committet (7 lokale Commits auf `main`, nicht gepusht). Inhalt der Session:

1. **Codebase-Refactoring** in zwei Wellen (Analyse durch 4 Opus-Agents, Umsetzung durch 3): totes Overview-Modul entfernt, `topN()` zentralisiert, Network-Filter-Listener vereinheitlicht; Pipeline verhaltensneutral aufgeraeumt (03c an Step-Muster angeglichen, 26 neue Unit-Tests, 2 immer-skippende Regression-Tests aktiviert, `known_issues` in baseline-metrics.json zentralisiert); Doku-Zahlen vereinheitlicht und Reconciliation-Widerspruch aufgeloest.
2. **Browser-Smoke-Test** (Playwright, headless Chromium): PASS. Alle drei Explore-Modi, Cross-View-Filterung, Listener-Stresstests ohne Fehler. Screenshots unter `c:\tmp\klawiter-smoke\`.
3. **`locationSameAs` implementiert**: Step 05 emittiert `klawiter:locationSameAs` (Wikidata-Entity-URI) fuer den Primaerort, 4.013 von 4.162 verorteten Eintraegen. Pipeline-Neulauf 05, 06, inject_provenance diff-verifiziert. Detail-View zeigt Wikidata-Link.
4. **22 unmatched Locations triagiert** in `data/output/unmatched_locations_review.md` (17 match-candidates, 3 ambiguous, 1 mojibake, 1 no-match). Nichts automatisch uebernommen.

Teststand: 437 collected; ohne llm/semantic alles gruen (353 passed); die 15 semantic-Failures sind pre-existing Ground-Truth-Abweichungen (76-Prozent-Niveau, in CLAUDE.md dokumentiert).

## Entscheidungen dieser Session (mit Begruendung)

- Eigene Property `klawiter:locationSameAs` statt `schema:sameAs`, weil sameAs am Entry das Werk mit dem Ort gleichsetzen wuerde.
- Mojibake-Regex-Konsolidierung, Sprachlisten-Dedup und SQL-Parser-Vereinheitlichung bewusst NICHT umgesetzt: nicht beweisbar verhaltensneutral ohne kompletten Pipeline-Neulauf.
- `publisher_normalize.json` als leeres Mapping angelegt statt den Code-Pfad zu entfernen: symmetrisch zu location_normalize.json, wird im Editor-Loop befuellt.
- Uncommittete Overview-Weiterarbeit verworfen (als Patch gesichert: `c:\tmp\explore-overview-uncommitted-2026-06-12.patch`), da das Modul seit Session 14f tot und nicht mehr lauffaehig war.

## Offene Faeden

- Editor-Review von `data/output/unmatched_locations_review.md` (fachliche Accept/Correct-Entscheidungen, Editor-in-the-Loop). Achtung Apostroph-Encoding: klawiter.json nutzt U+2019, locations.json U+0027.
- Kosmetisch: Header-Kommentar in `docs/js/explore-geography.js` sagt "Flat (default)", Code-Default ist `globe` (Zeile 36).
- UX-Detail: Wikidata-Link in der Detail-View steht hinter dem ganzen Orts-String, verweist aber nur auf den Primaerort.
- `.claude/settings.local.json` ist lokal modifiziert (Permission-Akkumulation), bewusst nicht committet.

## Der eine naechste Schritt

EIL-Verifikations-Interface (DIA-XAI-Pflicht-Deliverable): Verifikations-Workflow mit Provenance-Badges, Confidence-Ranking und Accept/Correct/Add-Aktionen. Kontext in [[about]] (Two EIL Roles, DIA-XAI Connection), Metriken-Definition in [[data]].

## Geteilt / gehalten

- Keine parallelen Lanes in diesem Repo zum Handoff-Zeitpunkt; alle Aenderungen dieser Session sind eigene Arbeit.
- Design-Kontrakt mit den SZD-Repos (GAMS Burgund/Gold) unveraendert.
