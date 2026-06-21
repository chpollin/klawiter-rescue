---
title: Handoff
tags: [process, transient]
updated: 2026-06-21
---

# Handoff-Notiz (Stand 2026-06-21, Session 17)

Transiente Prozessnotiz fuer den Wiedereinstieg einer frischen Instanz. Wird beim naechsten Handoff ueberschrieben. Projektdoku liegt in den uebrigen knowledge/-Dokumenten, Verlauf im [[journal]].

## Aktueller Stand

Session 17 (Forschungsleitstelle-Lane klawiter-rescue, Portfolio-Runde 2026-06-21). Zwei Straenge im Operator-Auftrag: Datenintegritaet SQL -> Frontend verifizieren, und den Ausbau des In-Tool-Editierens fuer die Expert-in-the-Loop-Kontrolle entwerfen.

1. **Record-Census gebaut und ausgefuehrt** (`pipeline/census.py`, Report `data/output/census-report.json`). Beweist reproduzierbar die Vollstaendigkeit des Datenflusses: 6.725 Quellseiten -> 6.725 JSON-LD-Eintraege 1:1 (kein Verlust, kein erfundener Datensatz, keine Dublette), Frontend = JSON-LD minus 1.546 Redirects = 5.179, ns0 6.296 = 4.751 angezeigt + 1.545 Redirects. Alle fuenf Rekonziliations-Checks PASS.
2. **Einzige Anomalie vollstaendig charakterisiert**: page_id 2979 ("A unidade espiritual do mundo"). Revisionsgeschichte-Trace ergab: die Seite hat drei Revisionen, die letzte (rev 18324, auf die page_latest zeigt) hat `rev_len = 0` — sie wurde drei Minuten nach Anlage geblankt. Nur zwei Kategorie-Stub-Revisionen ueberleben in den BLOBs (18044, 18045). Kein Pipeline-Fehler, sondern quellseitiger Verlust. Der Titel steht in der `zweig_page`-Tabelle und koennte propagiert werden (Einzeiler in `03_parse_entries.py`, Empty-Content-Zweig). Befund in [[data#known-problems]] praezisiert, Census in [[data#record-census]].
3. **Editier-Werkzeug-Spezifikation** ([[eil-editing]]): Zielentwurf fuer den Ausbau von edit.js — Editierbereich auf alle adjudizierbaren Felder, drei getypte Aktionen Accept/Correct/Add (EQUALIS-Triade), Unsicherheits-Oberflaeche aus Provenance + verify.py-Flags + Census, Persistenz (localStorage, Patch v2, apply_patches-Pipelineschritt, neuer Provenance-Zustand `editor`), Nachvollziehbarkeit als EQUALIS-Messsubstrat. Fuenf Build-Inkremente, minimaler naechster Schritt = Inkrement 1.

## Entscheidungen dieser Session

- Census als eigenes Werkzeug neben verify.py (Wert-Korrektheit) und 06_validate.py (Qualitaet): es prueft Record-Vollstaendigkeit, die bisher unbewiesene Achse.
- 2979 NICHT eigenmaechtig gefixt: ob die geblankte Seite mit Titel gezeigt oder ausgeschlossen wird, ist eine editorische Entscheidung. Census detektiert und dokumentiert sie, der Fix wird dem Operator vorgelegt.
- Kein Pipeline-Neulauf in dieser Runde: ein Neulauf regeneriert 6.725 Einzeldateien plus LLM-Schritt, grosser Diff; die Output-Regeneration gehoert in einen dedizierten Full-Run-Commit zusammen mit der 2979-Entscheidung.

## Offene Faeden

- **Operator-Entscheidung 2979**: geblankte Seite mit page_title als Titel zeigen (Einzeiler-Fix + Full-Run) oder als leere Seite ausschliessen.
- **Operator-Entscheidung Editier-Tool**: Bau der Inkremente aus [[eil-editing]] beauftragen; Inkrement 1 (Action-Typing + localStorage + Patch v2) ist der naechste Schritt. Frontend-Inkremente brauchen Browser-Verifikation.
- Editor-Review von `data/output/unmatched_locations_review.md` (aus Session 16, unveraendert offen).
- Kosmetik aus Session 16 unveraendert offen (Header-Kommentar explore-geography.js; Wikidata-Link-UX in Detail-View).

## Bereits gebaut (entscheidungsunabhaengig, ohne Browser)

- `knowledge/eil-editing.md` auf das szd-htr-Modell umgestellt (drei Status, Edit-History, kalibriertes Triage-Signal, lokaler Rueckschreibweg plus Git-Pruefpfad, gemeinsames Geruest dokumentiert, Modell-pluggable).
- `pipeline/apply_patches.py` plus `tests/test_apply_patches.py` (8 Tests gruen) und `data/corrections/` (Store mit README): die Rueckschreib- und Audit-Schicht. Overlay nach `inject_provenance`, Provenance `editor`, Edit-History, Review-Status, idempotent, leerer Store = No-Op. Backend-Teil von Inkrement 1/4.

## Der eine naechste Schritt

Operator-Klaerung der vier Gates (Reihenfolge, inhaltliche Stichprobe, 2979, Browser), dann der Frontend-Teil von Inkrement 1 (edit.js auf drei Status plus Accept/Correct/Add plus localStorage, Patch v2 wie von apply_patches erwartet) mit Browser-Sichtung, oder die 2979-Propagierung mit Full-Pipeline-Run.

## Geteilt / gehalten

- Keine parallelen Lanes in diesem Repo. Alle Aenderungen dieser Session sind eigene Arbeit, eigene Pfade committet.
- Census und Spezifikation sind additive Artefakte; klawiter.jsonld, frontend-JSON und Pipeline-Code inhaltlich unveraendert.
