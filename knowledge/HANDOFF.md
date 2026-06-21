---
title: Handoff
tags: [process, transient]
updated: 2026-06-21
---

# Handoff-Notiz (Stand 2026-06-21, Milestone-Runde)

Transiente Prozessnotiz fuer den Wiedereinstieg einer frischen Instanz. Wird beim naechsten Handoff ueberschrieben. Projektdoku liegt in den uebrigen knowledge/-Dokumenten, Verlauf im [[journal]], Quervergleich der Lane in `reports/synthese-klawiter-rescue.md` (Forschungsleitstelle-Repo).

## Aktueller Stand

Forschungsleitstelle-Lane klawiter-rescue, Portfolio-Runde 2026-06-21. Der Prototyp ist fertig und live (chpollin.github.io/klawiter-rescue) und seit dieser Runde autark. Der Operator-Auftrag laeuft in zwei Straengen: Datenintegritaet SQL -> Frontend (Strang 1, Vorrang) und Ausbau des In-Tool-Editierens fuer die Expert-in-the-Loop-Kontrolle (Strang 2). Die order dieser Runde hat den Werkzeugumfang freigegeben: komplettes Pruef- und Kurationswerkzeug bauen, beide Modellwege (Cloud und lokal), Werkzeug zuerst, Stichprobe danach, Browser-Sichtung ueber eine Chrome-Lane.

1. **Record-Census** (`pipeline/census.py`, Report `data/output/census-report.json`): beweist reproduzierbar die verlustfreie Uebernahme SQL -> JSON-LD -> Frontend, alle fuenf Rekonziliations-Checks PASS. Census in [[data#record-census]].
2. **Einzige Anomalie 2979** vollstaendig charakterisiert (geblankte Quellseite, quellseitiger Verlust, kein Pipeline-Fehler). Operator-Entscheidung gefallen: mit Titel zeigen. Einzeiler-Fix in `03_parse_entries.py` autorisiert, laeuft im naechsten Full-Run. Befund in [[data#known-problems]].
3. **Rueckschreib- und Audit-Schicht** (`pipeline/apply_patches.py` plus 8 Tests gruen, `data/corrections/`): Overlay nach `inject_provenance`, Provenance `editor`, Edit-History, Review-Status, idempotent. Backend-Teil von Editier-Inkrement 1. Spezifikation in [[eil-editing]].
4. **Frontend autark** (Commit ad270b1): vier JS-Bibliotheken und Schriften lokal vendoriert (docs/vendor/, docs/fonts/, favicon.svg), index.html auf lokale Pfade. Voller Reload ohne externen Request verifiziert. Anlass war eine CORS-Cache-Verunreinigung durch parallele localhost-Apps.
5. **Drei Strang-1-Datentreue-Fixes gelandet** (Milestone-Runde, getesteter Pipeline-Code): Location-Fix (6d3f6c0, Begrenzung auf den Publikationszeilen-Header; Nachtrag e2cfb1c, Trenner Doppelpunkt oder Punkt, verhindert einen Verlagsnamen als Ort bei page 14), Mojibake-Repair des Transliterations-Blocks (037e7d3), 2979 zeigen-mit-Titel (a0d128b). Vermessen gegen zwei committete, deterministische Artefakte: `data/output/location-fix-report.json` (4.751 ns0, 3.513 unveraendert, 443 geaendert, 795 gewonnen, 0 verloren, kein Verlagsname als Ort, Weimar 43/48) und `data/output/mojibake-repair-report.json` (62.351 Laeufe alle repariert, residual 0, idempotent). Voller Befund in [[validation]] (Fehlerklassen 1 und 3), Verlauf in [[journal]] (Session 18). Noch nicht im Frontend sichtbar, das regeneriert erst im Full-Run.

## Entscheidungen (Stand der order)

- Werkzeugumfang freigegeben: komplettes Werkzeug bauen, beide Modellwege, Werkzeug zuerst. Editier-Inkremente sind beauftragt, kein Gate mehr.
- 2979 mit Titel zeigen (order-Entscheidung, Empfehlung der Lane gefolgt).
- Die drei Strang-1-Fixes liegen jetzt als getesteter Code vor, die drei Bereinigungs-Teilprobleme aus der Vorrunde sind behandelt. Der Pipeline-Neulauf ist davon entkoppelt und wird zu einem reinen Ausfuehr-Schritt (Milestone 3).
- Milestone 3 (Full-Run mit 2979-Propagierung plus den drei Fixes) wird lokal autonom gebaut, der Push deployt GitHub Pages und ist daher operator-gated am Publish-Schritt. Aus dem Re-Run-Diff faellt die Stichprobe fuer die erste Operator-Verifikation.

## Offene Faeden

- **Einzige Operator-Entscheidung**: Multi-Edition-Seiten (427), im Editor kuratieren oder markieren und zurueckstellen. Blockiert den Rest nicht.
- **Editor-Review** von `data/output/unmatched_locations_review.md` (aus Session 16, unveraendert offen).
- Kosmetik aus Session 16 unveraendert offen (Header-Kommentar explore-geography.js, Wikidata-Link-UX in Detail-View).

## Der eine naechste Schritt

Milestone 3 bauen, der Full-Run, der die drei gelandeten Fixes plus die 2979-Propagierung erstmals in den Output und ins Frontend bringt. Lokaler Lauf, Diff und Screenshot-Spur autonom; Push operator-gated. Danach der Frontend-Teil von Editier-Inkrement 1 (edit.js auf drei Status plus Accept/Correct/Add plus localStorage, Patch v2 wie von apply_patches erwartet) mit Browser-Sichtung ueber die Chrome-Lane.

## Geteilt / gehalten

- Keine parallelen Lanes in diesem Repo. Alle Aenderungen sind eigene Arbeit, eigene Pfade committet.
- Census, Spezifikation und Weimar-Analyse sind additive Artefakte; klawiter.jsonld, frontend-JSON und Pipeline-Code inhaltlich unveraendert.
