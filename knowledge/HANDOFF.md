---
title: Handoff
tags: [process, transient]
updated: 2026-06-21
---

# Handoff-Notiz (Stand 2026-06-21, Konsolidierungsrunde)

Transiente Prozessnotiz fuer den Wiedereinstieg einer frischen Instanz. Wird beim naechsten Handoff ueberschrieben. Projektdoku liegt in den uebrigen knowledge/-Dokumenten, Verlauf im [[journal]], Quervergleich der Lane in `reports/synthese-klawiter-rescue.md` (Forschungsleitstelle-Repo).

## Aktueller Stand

Forschungsleitstelle-Lane klawiter-rescue, Portfolio-Runde 2026-06-21. Der Prototyp ist fertig und live (chpollin.github.io/klawiter-rescue) und seit dieser Runde autark. Der Operator-Auftrag laeuft in zwei Straengen: Datenintegritaet SQL -> Frontend (Strang 1, Vorrang) und Ausbau des In-Tool-Editierens fuer die Expert-in-the-Loop-Kontrolle (Strang 2). Die order dieser Runde hat den Werkzeugumfang freigegeben: komplettes Pruef- und Kurationswerkzeug bauen, beide Modellwege (Cloud und lokal), Werkzeug zuerst, Stichprobe danach, Browser-Sichtung ueber eine Chrome-Lane.

1. **Record-Census** (`pipeline/census.py`, Report `data/output/census-report.json`): beweist reproduzierbar die verlustfreie Uebernahme SQL -> JSON-LD -> Frontend, alle fuenf Rekonziliations-Checks PASS. Census in [[data#record-census]].
2. **Einzige Anomalie 2979** vollstaendig charakterisiert (geblankte Quellseite, quellseitiger Verlust, kein Pipeline-Fehler). Operator-Entscheidung gefallen: mit Titel zeigen. Einzeiler-Fix in `03_parse_entries.py` autorisiert, laeuft im naechsten Full-Run. Befund in [[data#known-problems]].
3. **Rueckschreib- und Audit-Schicht** (`pipeline/apply_patches.py` plus 8 Tests gruen, `data/corrections/`): Overlay nach `inject_provenance`, Provenance `editor`, Edit-History, Review-Status, idempotent. Backend-Teil von Editier-Inkrement 1. Spezifikation in [[eil-editing]].
4. **Frontend autark** (Commit ad270b1): vier JS-Bibliotheken und Schriften lokal vendoriert (docs/vendor/, docs/fonts/, favicon.svg), index.html auf lokale Pfade. Voller Reload ohne externen Request verifiziert. Anlass war eine CORS-Cache-Verunreinigung durch parallele localhost-Apps.
5. **Weimar-Fix entworfen und vermessen** (Commit a482112, nur Wissensdokumente): Location-Extraktion auf die Publikationszeile begrenzen korrigiert 30 der 48 Weimar-Faelle und gewinnt 508 bisher fehlende Orte. Drei Bereinigungs-Teilprobleme benannt. Volle Charakterisierung in [[validation]] (Fehlerklasse 1). Noch nicht im Pipeline-Code gelandet.

## Entscheidungen (Stand der order)

- Werkzeugumfang freigegeben: komplettes Werkzeug bauen, beide Modellwege, Werkzeug zuerst. Editier-Inkremente sind beauftragt, kein Gate mehr.
- 2979 mit Titel zeigen (order-Entscheidung, Empfehlung der Lane gefolgt).
- Weimar-Fix nicht halbfertig committen: er landet erst mit den drei Teilproblemen und gemeinsam mit dem Mojibake-Repair.
- Kein Pipeline-Neulauf in dieser Runde: 2979-Propagierung, Weimar-Fix und Mojibake-Repair gehoeren in einen dedizierten Full-Run-Commit.

## Offene Faeden

- **Einzige Operator-Entscheidung**: Multi-Edition-Seiten (427), im Editor kuratieren oder markieren und zurueckstellen. Blockiert den Rest nicht.
- **Editor-Review** von `data/output/unmatched_locations_review.md` (aus Session 16, unveraendert offen).
- Kosmetik aus Session 16 unveraendert offen (Header-Kommentar explore-geography.js, Wikidata-Link-UX in Detail-View).

## Der eine naechste Schritt

Weimar-Fix im Pipeline-Code landen (drei Teilprobleme plus Mojibake-Repair, dann Full-Run mit 2979-Propagierung, Re-Run-Diff als Stichprobe fuer die Operator-Verifikation), parallel der Frontend-Teil von Editier-Inkrement 1 (edit.js auf drei Status plus Accept/Correct/Add plus localStorage, Patch v2 wie von apply_patches erwartet) mit Browser-Sichtung ueber die Chrome-Lane.

## Geteilt / gehalten

- Keine parallelen Lanes in diesem Repo. Alle Aenderungen sind eigene Arbeit, eigene Pfade committet.
- Census, Spezifikation und Weimar-Analyse sind additive Artefakte; klawiter.jsonld, frontend-JSON und Pipeline-Code inhaltlich unveraendert.
