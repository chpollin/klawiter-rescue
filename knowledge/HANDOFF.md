---
title: Handoff
tags: [process, transient]
updated: 2026-07-18
---

# Handoff-Notiz (Stand 2026-07-18, Modellierungsrunde Session 22)

Transiente Prozessnotiz fuer den Wiedereinstieg einer frischen Instanz. Wird beim naechsten Handoff ueberschrieben. Projektdoku liegt in den uebrigen knowledge/-Dokumenten, Verlauf im [[journal]], Quervergleich der Lane in `reports/synthese-klawiter-rescue.md` (Forschungsleitstelle-Repo).

## Aktueller Stand

Zwei Runden am 2026-07-18, beide gepusht, Baum sauber, main synchron mit origin.

**Session 21, Umsetzungsrunde.** Die Editierschicht implementiert die Increments 1 bis 3 aus [[eil-editing]]: Pruefhinweise je Eintrag aus `docs/data/triage.json` (`pipeline/build_triage.py`, kein Score, Hinweise erloeschen mit der Adjudikation) und Quell-Evidenz je Feld mit ehrlichem Volltext-Fallback. Kontrakte gepinnt (`tests/test_patch_contract.py`, `tests/test_triage.py`, `tests/evidence_triage.test.js` via `tests/test_frontend_logic.py`, braucht Node, skippt sonst), Browser-Verifikation auf localhost bestanden. Nach jedem Pipeline-Lauf `python pipeline/build_triage.py` mitlaufen lassen (in `pipeline/README.md` eingetragen).

**Session 22, Modellierungsrunde (rein konzeptuell, kein Code).** Neues [[edition-model]] als Entscheidungsgrundlage fuer die Multi-Edition-Gate-Frage: Multi-Edition ist ein Ebenenfehler (Seite = Werk, `'''[Jahr]:'''`-Bloecke = Ausgaben), Zielmodell ist die Werk/Ausgabe-Trennung in schema.org (`workExample`/`exampleOfWork`) im vorhandenen JSON-LD-Stack, Vorbedingung ein stabiles ID-Schema `klawiter:edition/{pageId}-{jahr}-{laufbuchstabe}`. Dazu Evidenz als Web Annotation, Provenienz als PROV-O-Sidecar (das `_provenance`-Feld bleibt abgeleitete Frontend-Kurzform), Pruefschicht SHACL/EARL/DQV, skizziert als schmales PROV-Profil `llmprov`. [[production-readiness]] Arbeitspaket 1 entsprechend umformuliert, [[ontology]] um den Verweis-Abschnitt Work/Edition Extension ergaenzt, [[index]] registriert das Dokument. Details in [[journal]] Session 22.

## Offene Operator-Punkte

Die vier Gate-Fragen stehen unveraendert in [[production-readiness#braucht-den-operator]]; die Entscheidungsgrundlage fuer Gate 1 liegt seit Session 22 in [[edition-model]], und Gate 1 ist Gate 2 und 3 vorgelagert (erst die Ausgaben-Ebene macht Reconciliation-Tiefe und Wiki-Druck-Merge sauber entscheidbar):

1. Multi-Edition-Behandlung: dekomponieren und kuratieren oder markieren und zurueckstellen? (Entscheidungsgrundlage [[edition-model]], Stichproben-Gate an drei Seiten vor jedem Vollauf)
2. Reconciliation-Tiefe fuer die Produktionsreife.
3. Wiki-Druck-Merge im Scope der ersten Produktionsreife (nutzt dasselbe Provenienz-Schema).
4. Modellweg im Auslieferungsstand (Cloud plus Patch-Datei-Export als Fallback, oder auch lokaler Write-Back-Endpunkt). Daran haengt Increment 4.

Zusaetzlich zur Klaerung: ob der knowledge-Frontmatter repo-weit auf den Promptotyping-Pflichtkern (`project`, `method`, `status`) geliftet werden soll (bewusst nicht angefasst, waere ein invasiver Eingriff ueber alle Dateien).

Innerhalb des Zielmodells offen und der Editorin vorzulegen: Auflagen-Unterzeilen als eigene Knoten oder strukturierte Beschreibung; Sammelband-Vorkommen ueber `schema:isPartOf`. Vor einer Praegung des `llmprov`-Profils steht die Nachbarschaftspruefung (W3C ML Schema u.a.) aus.

## Der eine naechste Schritt

Operator-Entscheid zu Gate 1 (Multi-Edition) einholen; bei "dekomponieren" startet das Stichproben-Gate aus [[edition-model#vorgehen]]. Unabhaengig davon anschlussfaehig: die stratifizierte Feld-Stichprobe (Rest von M3.8, [[validation#method-and-limits]]) als Kalibrierungs-Input fuer die Triage-Klassenordnung, oder der M3-Daten-Publish (lokal verifiziert, wartet auf den Publish-Push).

## Geteilt / gehalten

- Keine parallelen Lanes in diesem Repo. Alle Aenderungen sind eigene Arbeit, eigene Pfade committet.
- Session 22 hat keine Daten- oder Code-Dateien angefasst; `klawiter.json`, `klawiter.jsonld`, Pipeline und Editierschicht sind unveraendert auf Stand Session 21. Die Editierschicht bleibt localhost-gated und fuer Besucher inert.
- Bekannte Vorbefunde der Testsuite (Multi-Edition-Ground-Truth in `test_semantic`, LLM-Judge ohne Key, fehlende Intermediates fuer `test_real_entries`/`test_llm_judge`) bestehen unveraendert, auf sauberem Baum identisch reproduziert.
