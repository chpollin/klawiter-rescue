---
title: Handoff
tags: [process, transient]
updated: 2026-07-18
---

# Handoff-Notiz (Stand 2026-07-18, Konzeptuelle Runde Session 20)

Transiente Prozessnotiz fuer den Wiedereinstieg einer frischen Instanz. Wird beim naechsten Handoff ueberschrieben. Projektdoku liegt in den uebrigen knowledge/-Dokumenten, Verlauf im [[journal]], Quervergleich der Lane in `reports/synthese-klawiter-rescue.md` (Forschungsleitstelle-Repo).

## Aktueller Stand

Rein konzeptuelle Runde vom 2026-07-18, keine Implementierung, kein Pipeline-Lauf. Drei Stränge abgeschlossen.

**EQUALIS restlos entfernt.** EQUALIS ist durch das Evaluationskonzept DIA-XAI im Obsidian-Vault abgeloest. Die Bewertung ist hermeneutisch-qualitativ; messbarer Baustein ist der im Werkzeug verifizierte Gold Standard. Alle Stellen in `about.md`, `data.md`, `eil-editing.md` und `journal.md` sind auf diese Rahmung umgestellt; die Git-History haelt den frueheren Stand.

**knowledge-Ordner nach Promptotyping-Konvention refactoriert.** `index.md` ist selbsttragend und aktuell gemacht: volatile Statuszahlen entfernt, `HANDOFF` und `eil-editing`/`production-readiness` korrekt in der Navigation aufgenommen, operative Open-Items durch positive Verweise auf die Funktionstraeger ersetzt.

**Konzeptdokument `production-readiness.md` angelegt.** Arbeitet die Produktionsreife des EIL-Kurationswerkzeugs aus: Ist-Stand Frontend und Datenbasis, die zwei ineinandergreifenden Loops (Developer-in-the-Loop auf Pipeline-Ebene, Editor-in-the-Loop auf Datenebene), Provenienz-Schichten als Verifikationsgrundlage, Gold Standard als messbarer Baustein, Korrektur-Protokoll als Dokumentationsgrundlage sowie sechs geordnete Arbeitspakete (Multi-Edition-Dekomposition, Redirect-Aufloesung, Kategorie-Seiten, Reconciliation-Vorbereitung, Wiki-Druck-Merge, Deployment mit Zitierbarkeit).

Technischer Vorlaufstand ist die Milestone-Runde (Session 18/19): Increment 1 der Editierschicht gebaut und browser-verifiziert, alle drei Strang-1-Fixes gelandet (Location, Mojibake, 2979), M3-Vorschau lokal gefahren und zurueckgesetzt, Publish-Push wartet auf Operator-Freigabe.

## Offene Operator-Punkte

Die vier Gate-Fragen stehen in [[production-readiness#braucht-den-operator]]:

1. Multi-Edition-Behandlung im Editor: dekomponieren und kuratieren oder markieren und zurueckstellen? (steht seit der Milestone-Runde offen)
2. Reconciliation-Tiefe fuer die Produktionsreife.
3. Wiki-Druck-Merge im Scope der ersten Produktionsreife.
4. Modellweg im Auslieferungsstand (Cloud plus Patch-Datei-Export als Fallback, oder auch lokaler Write-Back-Endpunkt).

Zusaetzlich zur Klaerung: ob der knowledge-Frontmatter repo-weit auf den Promptotyping-Pflichtkern (`project`, `method`, `status`) geliftet werden soll (bewusst nicht in der konzeptuellen Runde angefasst, waere ein invasiver Eingriff ueber alle Dateien).

## Der eine naechste Schritt

Operator-Entscheid zu den Gate-Fragen in [[production-readiness#braucht-den-operator]] abwarten. Danach Arbeitspaket 1 (Multi-Edition-Dekomposition) oder M3-Daten-Publish aufgreifen, je nach Operator-Entscheid. M3 ist lokal verifiziert und wartet nur auf den Publish-Push.

## Geteilt / gehalten

- Keine parallelen Lanes in diesem Repo. Alle Aenderungen sind eigene Arbeit, eigene Pfade committet.
- Census, Spezifikation, Mess-Artefakte und das neue Konzeptdokument sind additive Artefakte; klawiter.jsonld, frontend-JSON und Pipeline-Code inhaltlich unveraendert.
