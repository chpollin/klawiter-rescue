---
title: Handoff
tags: [process, transient]
updated: 2026-07-18
---

# Handoff-Notiz (Stand 2026-07-18, Umsetzungsrunde Session 21)

Transiente Prozessnotiz fuer den Wiedereinstieg einer frischen Instanz. Wird beim naechsten Handoff ueberschrieben. Projektdoku liegt in den uebrigen knowledge/-Dokumenten, Verlauf im [[journal]], Quervergleich der Lane in `reports/synthese-klawiter-rescue.md` (Forschungsleitstelle-Repo).

## Aktueller Stand

Umsetzungsrunde vom 2026-07-18 nach Operator-Freigabe (Push freigegeben 18.07.). Die Editierschicht implementiert jetzt die Increments 1 bis 3 aus [[eil-editing]]; Details und Verifikation in [[journal]] Session 21.

**Increment 2 gebaut.** `pipeline/build_triage.py` erzeugt `docs/data/triage.json` aus den committeten verify.py- und Census-Reports; `edit.js` buendelt die Flags mit den Provenienz-Schichten zu geordneten Pruefhinweisen je Eintrag (Detail-Block, Karten-Chip, Feld-Marker, Sortierung "Pruefbedarf zuerst", nur im Edit-Modus). Kein Score, keine Metrik-Ableitung; Hinweise erloeschen mit der Adjudikation des Felds.

**Increment 3 gebaut.** Quell-Evidenz neben jedem der vier getrackten Felder: feldgenauer Ausschnitt mit markiertem Treffer und Fundstellenzaehler, fuer missing-Felder der verify.py-detektierte Rohwert, sonst der ganze Quelltext einklappbar als ehrlicher Fallback.

**Kontrakte gepinnt.** Patch-v2-Kontrakt unveraendert und gruen (`tests/test_patch_contract.py`). Neu gepinnt: Triage-Artefakt-Schema (`tests/test_triage.py`), Evidenz- und Hinweis-Logik (`tests/evidence_triage.test.js` via `tests/test_frontend_logic.py`, braucht Node, skippt sonst). Browser-Verifikation auf localhost durchgefuehrt (Playwright, manuell-aequivalent), kein neuer Request auf dem oeffentlichen Pfad, Frontend bleibt autark.

**Regenerierungs-Hinweis.** `triage.json` haengt an den committeten Reports; nach jedem Pipeline-Lauf `python pipeline/build_triage.py` mitlaufen lassen (in `pipeline/README.md` eingetragen).

## Offene Operator-Punkte

Die vier Gate-Fragen stehen unveraendert in [[production-readiness#braucht-den-operator]]:

1. Multi-Edition-Behandlung im Editor: dekomponieren und kuratieren oder markieren und zurueckstellen? (steht seit der Milestone-Runde offen)
2. Reconciliation-Tiefe fuer die Produktionsreife.
3. Wiki-Druck-Merge im Scope der ersten Produktionsreife.
4. Modellweg im Auslieferungsstand (Cloud plus Patch-Datei-Export als Fallback, oder auch lokaler Write-Back-Endpunkt). Daran haengt Increment 4.

Zusaetzlich zur Klaerung: ob der knowledge-Frontmatter repo-weit auf den Promptotyping-Pflichtkern (`project`, `method`, `status`) geliftet werden soll (bewusst nicht angefasst, waere ein invasiver Eingriff ueber alle Dateien).

## Der eine naechste Schritt

Operator-Entscheid zu den Gate-Fragen abwarten. Unabhaengig davon anschlussfaehig: die stratifizierte Feld-Stichprobe (Rest von M3.8, [[validation#method-and-limits]]) als Kalibrierungs-Input fuer die Triage-Klassenordnung, oder der M3-Daten-Publish (lokal verifiziert, wartet auf den Publish-Push).

## Geteilt / gehalten

- Keine parallelen Lanes in diesem Repo. Alle Aenderungen sind eigene Arbeit, eigene Pfade committet.
- `docs/data/triage.json` ist ein additives Artefakt; `klawiter.json`, `klawiter.jsonld` und Pipeline-Code inhaltlich unveraendert. Die Editierschicht bleibt localhost-gated und fuer Besucher inert.
- Bekannte Vorbefunde der Testsuite (Multi-Edition-Ground-Truth in `test_semantic`, LLM-Judge ohne Key, fehlende Intermediates fuer `test_real_entries`/`test_llm_judge`) bestehen unveraendert, auf sauberem Baum identisch reproduziert.
