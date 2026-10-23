---
title: Claim check of the blog post v4
status: complete
language: de
created: 2026-10-23
related: [status, data, print-wiki-merge]
---

# Claims-Tabelle blog-v4 (Stand b0c63ea)

Alle Repository-Artefakte wurden mit `git show b0c63ea:<pfad>` gelesen, unabhängig vom Arbeitsbaum. Die Daten sind seit 7994ccb unverändert, b0c63ea ändert nur `knowledge/`. Seite 1140 wurde roh aus `data/raw/zt_05` (Text-ID 48154, laut `docs/data/klawiter.json` die aktuelle Fassung von Seite 1140) gelesen, nur lesend. Keine Netzabfragen, kein Link live geprüft.

Urteil: gestützt (unverändert gegenüber v2 und belegt), angepasst (gegenüber v2 umformuliert oder neu, belegt), entfernt (aus v2 gestrichen), Betreiber (nicht aus dem Repository belegbar, Slot oder Betreiberangabe). Zeilen, die sich gegenüber v3 geändert haben oder neu sind, tragen in der Spalte Urteil den Vermerk v4 mit dem Review-Punkt. Neue Zeilen tragen Nummern ab 100.

Deploy-Vorbehalt (Review Blocker 1): Alle Werte gelten für b0c63ea. Die lokale Referenz origin/main (10966ab, 2026-10-23 15:46) enthält 7994ccb nicht. Dort stehen in `llm-enrichment-report.json` `fieldsFilled` 282/249/322/35, `rejectedCachedValues` 24 und kein `rejectedNotInSource`, in `reconciliation/manifest.json` `publishableLocationLinks` 354, gelesen mit `git show 10966ab:<pfad>` ohne Netzabfrage. Der Text trägt dafür PRÜFEN-Kommentare am Kopf, am LLM-Absatz und an der Zahl 334.

## Einleitung

| Nr. | Aussage in v3 | Quelle bei b0c63ea | Wert | Urteil |
|---|---|---|---|---|
| 1 | Klawiter, Germanist an der University of Notre Dame | Seite 1140 (Promotion im German Department, Faculty Workstation Program für „all faculty members“ in Notre Dame); `knowledge/about.md`; `CITATION.cff` `authors[0].affiliation` = University of Notre Dame | Notre Dame | gestützt, v4 Quelle CITATION.cff ergänzt (Minor) |
| 2 | Über Jahrzehnte, Inhaltsarten Werke, Ausgaben, Übersetzungen, Korrespondenz, Forschungsliteratur, Verfilmungen, Dramen | Seite 1140 („for the past 50 years“); `docs/data/klawiter.json` `_meta.entryTypes` (correspondence 111, secondary-literature 1407, film 93, drama 42) | | v4 angepasst, „Bühnenfassungen“ → „Dramen“, weil `dramatic-reading` (18) Lesungen meint (Minor) |
| 3 | Erste Zweig-Bibliographie 1965 als Band 50 der UNC Studies in the Germanic Languages and Literatures | Seite 1140 roh: „my first Zweig bibliography appeared in print in 1965 as Number Fifty of the University of North Carolina Studies …“ | 1965, Nr. 50 | gestützt |
| 4 | 1991 neue Bibliographie bei Ariadne Press, „Stefan Zweig. An International Bibliography“ | `knowledge/print-volumes.md` (Tabelle der Dateien; Brief vom 17.08.2009 „Riverside, CA.: Ariadne Press, 1991“) | 1991 | angepasst (v2 „erweiterte Ausgabe“) |
| 5 | 1999 erstes Addendum bei Ariadne Press | `knowledge/print-volumes.md` („Addendum I, Ariadne Press, 1999“); Seite 1140 („first addendum … in 1999“) | 1999 | gestützt |
| 6 | Dezember 2008 Prototyp des Wikis durch den Sohn | Seite 1140 roh: „In the first few weeks in December 2008, [the son] assembled a prototype Wiki“ | Dez. 2008 | angepasst (v2 „Ab Ende 2008 führte Klawiter … fort“) |
| 7 | Dauerhafte Unterkunft an SUNY Fredonia, deren Reed Library eine Stefan-Zweig-Sammlung besitzt | Seite 1140 roh: „the Reed Library with its Stefan Zweig Collection … Fredonia expressed an interest in housing the online resource“ | | angepasst (v2 „betrieben wurde“ ohne Vorgeschichte) |
| 8 | Wiki-Titel „Stefan Zweig Bibliography“ | `knowledge/about.md` (Titel „after the wiki“) | | gestützt |
| 9 | Wiki nach 2021 nicht mehr bearbeitet | `knowledge/journal.md` 2026-10-21 („The wiki was not edited after the 2021 dump“) | 2021 | gestützt |
| 10 | „seit 2023“ für die Zwischenlösung | kein Beleg | | entfernt |
| 11 | Zwischenlösung „bei Digital Humanities Craft“, „aus einer Sicherung wiederhergestellt“ | `knowledge/journal.md` 2026-10-21 nennt nur Cloud Run im Google-Cloud-Projekt `klawiter-szd`, keinen Betreiber und keine Sicherung | | entfernt (v3: „Eine Kopie lief zuletzt als Zwischenlösung auf Google Cloud“) |
| 12 | Abschaltung Oktober 2026 wegen fehlender Sicherheitsupdates, in Abstimmung mit dem Literaturarchiv Salzburg | `knowledge/journal.md` 2026-10-21 (PHP 8.1 ohne Sicherheitsupdates, „in agreement with the project partner at the Literaturarchiv Salzburg“) | 21.10.2026 | gestützt |
| 13 | klawiter.stefanzweig.digital soll weiterleiten | `knowledge/journal.md` 2026-10-21, Open | | gestützt |
| 14 | „Die Daten sind für die Zweig-Forschung wertvoll, aber komplex.“ | Slogan, kein Sachgehalt | | entfernt (Review-Minor) |
| 15 | Wiki-Markup in Datenbank, mehrere Publikationen pro Seite, Sonderzeichen beschädigt | `knowledge/about.md` (SQL-Dump), `knowledge/data.md` Z. 49, `data/output/mojibake-repair-report.json` | | gestützt |
| 16 | Ziel Übergabe an Stefan Zweig Digital in GAMS | `knowledge/print-wiki-merge.md` („delivery targets Stefan Zweig Digital in GAMS“, „for delivery as TEI to Stefan Zweig Digital“) | | angepasst (v2 „langfristig zu archivieren“ ohne Beleg) |

## Warum die Rettung jetzt möglich ist

| Nr. | Aussage | Quelle | Wert | Urteil |
|---|---|---|---|---|
| 17 | Frontier-LLM, Claude Code, Name und Version | Claude Code in `knowledge/coordination.md`; Name/Version Slot | | Betreiber |
| 18 | Das Projekt arbeitet nach Promptotyping | `knowledge/journal.md` Frontmatter (Promptotyping), `knowledge/` als Wissensbasis | | gestützt, v4 Perspektive „Wir“ → „Das Projekt“ (Minor) |
| 19 | LLM-Agenten prüften auch die Zuordnung der Ortsangaben zu Wikidata | `data/reconciliation/location-decisions.json` `decidedBy`; `knowledge/status.md` (Runde 23.09.) | | angepasst |
| 20 | Gemini 3.1 Flash-Lite in Vorschauversion ergänzt fehlende Angaben, vom Projekt als kostengünstig eingeschätzt | `data/output/llm-enrichment-report.json` `model` | gemini-3.1-flash-lite-preview | gestützt, v4 „kostengünstig“ als Einschätzung markiert (Minor), die Einschätzung selbst ist Betreiberangabe |
| 21 | Budget-Halbsatz, Rettung ohne Frontier-LLMs „nach Einschätzung des Projekts“ nicht möglich | Betreiberaussage | | Betreiber, v4 als Einschätzung formuliert, Perspektive vereinheitlicht (Minor) |
| 22 | Prototyp macht alle aktuellen Seiten zugänglich | `knowledge/status.md` (6.725 / 6.725 canonical records), `CITATION.cff` abstract | | gestützt |
| 23 | Zahlenstand 23. Oktober 2026 | Commit b0c63ea, 23.10.2026 | | angepasst (neu) |

## Was der Prototyp leistet

| Nr. | Aussage | Quelle | Wert | Urteil |
|---|---|---|---|---|
| 24 | Datenbankexport enthält frühere Fassungen | `knowledge/data.md` Source scope, `data/reconciliation/source-revision-decisions.json` (Revisionen) | | gestützt |
| 25 | aktuelle Seiten [N1] | `data/output/quality-report.json` `summary.total_entries` | 6725 | angepasst (Slot gefüllt) |
| 26 | Einträge der Bibliographie [N2] | `docs/data/klawiter.json` `_meta.ns0Count`; `quality-report.json` `summary.non_redirects_main` | 4758 | angepasst (Slot gefüllt) |
| 27 | Weiterleitungen | `quality-report.json` `summary.redirects` | 1538 (Frontend `_meta.redirectCount` 1555 zählt 17 Titelaliase mit, laut `knowledge/status.md`) | angepasst (neu) |
| 28 | übrige Seiten Kategorien und technische Seiten | `quality-report.json` `non_redirects_all − non_redirects_main` | 5187 − 4758 = 429 | gestützt |
| 29 | reparierte Zeichenfolgen [R] | `data/output/mojibake-repair-report.json` `runs.repaired` (Kontrolle `residual_entries_after_repair`) | 62351 (Rest 0) | angepasst (Slot gefüllt) |
| 30 | Wartungskonto überschrieb Inhaltsseiten wie „Maria Stuart“ | `source-revision-decisions.json` `fixerActor` = „Redirect fixer“, Entscheidung zu Seite 35 „Maria Stuart“ | | gestützt |
| 31 | wiederhergestellte Seiten [G] aus der letzten von Hand bearbeiteten Fassung | `source-revision-decisions.json` `decisions[]` mit `action = restore-human-revision`; `rule` („to the last human revision“) | 8 (eine davon Kategorieseite 4248, Namensraum 14) | angepasst (v2 „Fassung des Kompilators“) |
| 32 | offene Fälle [H], überschriebene Fassung fehlt im Export | `source-revision-decisions.json` `action = withhold-redirect-relation`; `reconciliation/manifest.json` `counts.contestedSourceRevisionClaims` | 10 / 10 | angepasst (Slot gefüllt) |
| 33 | deutsches Buch 2000 neben arabischem Artikel 2015 | `knowledge/data.md` Z. 49 (Seite 4445), `knowledge/evaluations/2026-09-05/source-only.json` | | gestützt |
| 34 | Seiten mit Publikationsebene [N3] | `docs/data/klawiter.json` `_meta.publicationCoverage.pages` | 1665 | angepasst (Slot gefüllt, „mit Jahresangabe“ gestrichen, `knowledge/status.md` spricht von „publication header“) |
| 35 | Publikationen [M] | `_meta.publicationCoverage.publications` | 3273 | angepasst (Slot gefüllt) |
| 36 | Zuordnung Impressum, Sprache, Umfang, Beiträge, Rollen; Verweis auf Stelle im Wiki-Text | `knowledge/status.md` (publication layer, „bound to their own source slice“) | | gestützt |
| 37 | Zusammenhang weiterer Publikationen als Übersetzung oder Werkfassung bleibt offen | `knowledge/status.md` (full bibliographic modelling open), `knowledge/data.md` („does not yet model every translator … relation“) | | gestützt, v4 an den Werk-/Ausgabengraph angepasst |
| 38 | LLM füllt nur leere Felder Verlag, Ort, Übersetzer, Seitenzahl | `pipeline/03b_llm_enrich.py` `merge_result` | | gestützt |
| 39 | Prompt verlangt nur ausdrücklich Genanntes | `pipeline/lib/llm_extract.py` `SYSTEM_PROMPT` („Extract ONLY what is explicitly stated“) | | gestützt |
| 40 | Prüfung gegen den gesamten Eintragstext, nur Verlag, Ort, Übersetzer | `pipeline/03b_llm_enrich.py` Z. 259–283 (`source = raw_content`, Schleife über publisher/location/translator, `occurs_in_source`) | | angepasst (M3, v2 „Quellzeile“ und „Seitenzahl“) |
| 41 | Verlagswert mit Beitragsangabe wird verworfen | `03b_llm_enrich.py` `names_a_contribution_credit`; `pipeline/lib/patterns.py` | | angepasst |
| 42 | Seitenzahlen ohne Textprüfung | `03b_llm_enrich.py` (page_count wird ohne `occurs_in_source` übernommen, nur Off-by-one-Korrektur in `_correct_page_count`) | | angepasst (neu) |
| 43 | gefüllte Felder [A] | `data/output/llm-enrichment-report.json` `fieldsFilled` 266 + 240 + 243 + 35 | 784 | angepasst (Slot gefüllt) |
| 44 | verworfene Werte [B] | `llm-enrichment-report.json` `rejectedCachedValues` | 144 | angepasst (Slot gefüllt) |
| 45 | davon nicht im Eintrag | `rejectedNotInSource` 60 + 25 + 35 | 120 | angepasst (neu) |
| 46 | eingefroren mit LLM-Name und Prüfsummen von Prompt, Eingabe, Ergebnis; Lauf ohne LLM-Aufruf | `llm-enrichment-report.json` `frozenProvenance` (`model`, `promptSha256`, `parsedInputSha256`, `resultsSha256`), `mode = frozen`, `networkCallsMade = false` | | gestützt |
| 47 | Herkunftsangabe der Kernfelder regelbasiert / LLM / nicht vorhanden | `docs/data/klawiter.json` `_provenance`; `docs/js/detail.js` `_provBadge` (R, L, —) in der Leseansicht | | gestützt |

## Mehrdeutigkeiten bleiben sichtbar

| Nr. | Aussage | Quelle | Wert | Urteil |
|---|---|---|---|---|
| 48 | „Manche Unschärfen gehören zur Quelle.“ | Einleitungsformel | | entfernt |
| 49 | St. Petersburg Russland oder Florida, ohne Verknüpfung, beide Lesarten verzeichnet | `data/output/reconciliation/contested-claims.json` (Claim St. Petersburg, Lesarten Q656, Q49236, no-assignment, `claimStatus` contested); `knowledge/journal.md` Session 40 („St. Petersburg (Russia or Florida)“) | | gestützt |
| 50 | Orte mit Fragezeichen ohne Verknüpfung | `knowledge/journal.md` Session 40 Decided; `location-decisions.json` `unresolved` für Tashkent?, Jakarta?, Prishtina?, Tirana? | 4 der 12 offenen | gestützt |
| 51 | abweichende Namensformen und Umfangsangaben nebeneinander | `knowledge/data.md` (review flag `extent-differs-across-source-pages`) | | gestützt |
| 52 | Drei Zustände für Ausgabenzuordnung und Wikidata-Verknüpfung | `knowledge/data.md` Statement states; `data/output/editions/manifest.json` `confirmedEditions` 76, `editions` 2077 | | gestützt |
| 53 | Definition „bestätigt“, Ortsverknüpfungen erfüllen sie nicht, Delegation, Kennzeichnung als von Agenten geprüft | Wortlaut nach Review B1 (v3); `knowledge/data.md` Provenance; `location-decisions.json` `decidedBy` nur `independent-verification-agent` (350) und `main-instance` (8) | | angepasst, in v4 unverändert, OPERATOR-Kommentar bleibt |
| 54 | Die Anwendung nennt den Entscheider bei Ortsentscheidungen, in der Prüfgeschichte offener und entschiedener Aussagen zu Normdaten und Ausgaben und bei wiederhergestellten oder zurückgehaltenen Seiten | `git show b0c63ea:docs/js/detail.js` Z. 227–228 (`Decided by …reviewed_by` am Prüfstatus), Z. 508–512 `_authorityHistory` (`item.decidedBy`), Z. 532 `withheldRedirectBlock` (`item.decidedBy`), Z. 554–572 `_sourceRevisionNote` (`human.actor`, `rev.decidedBy` im Hilfetext), Z. 600–603 `_editionClaimArticle` (`item.reviewer`) | | v4 korrigiert (Blocker 3), die v3-Aussage „nur bei den Ortsentscheidungen“ war falsch |
| 55 | Entscheider steht als freier Text, eine feste Unterscheidung von Regel, LLM-Agent und Person fehlt | `knowledge/data.md` Provenance („copies the decider as a free string into `reviewed_by`“, „A typed producer class that keeps rule, LLM agent and person apart belongs to the shared claim schema planned …“) | | v4 neu (Blocker 3), Verweis auf Lab-Prototypen gestrichen (Minor) |
| 56 | 323 Verknüpfungen aus dem Prüfdurchgang vom 23.09.2026, LLM-Agenten prüften die unentschiedenen Ortsangaben an Belegstellen und Wikidata, Hauptagent entschied nach einheitlichem Regelwerk | `location-decisions.json` confirm 307 + correct 16 mit `evidence` `location-agent-review-2026-09-23.json` und `provenance` „reviewed by independent agents … adjudicated by the main instance“; `location-agent-review-2026-09-23.json` `description`; `knowledge/journal.md` Session 40 („Three agents reviewed the undecided place subjects in parallel“) | 323 | v4 korrigiert (Major), „drei Agenten … jeden Kandidaten“ gestrichen, weil die Review-Datei je Subjekt eine Aktion plus Adjudikation festhält |
| 57 | Sechs Links nur auf Low-Score-Prüfung ohne verankerte Belegstelle | `location-decisions.json`, `action` confirm/correct ohne `sourceOccurrence`, `evidence` nur `location-low-score-review.json#…` (Nicosia, Borås, Luxembourg, Rio de Janiero, Yanji, Bambaī); `location-low-score-review.json` `case_decisions[].local_evidence.source_slice` zitiert Text, `verifier_provenance` ein Agent | 6 | angepasst (M1, neu) |
| 58 | Ortsangaben [C] | `data/output/reconciliation/manifest.json` `counts.locationSubjects`; `docs/data/reconciliation.json` `summary.locationSubjects` | 382 | angepasst (Slot gefüllt) |
| 59 | verknüpft [D] | `manifest.json` `counts.publishableLocationLinks`; `publishable-links.json` `locations` (334 Schlüssel); confirm 315 + correct 19 in `location-decisions.json` | 334 | angepasst |
| 60 | strittig offen [E] | `location-decisions.json` `action = unresolved`; `manifest.json` `counts.contestedAuthorityClaims` (alle 12 sind Orts-Claims mit `decisionStatus` open in `contested-claims.json`) | 12 | angepasst |
| 61 | als Ganzes nicht verknüpft, mehrere Orte in einer Angabe [F] | `location-decisions.json` `action = reject`, alle Subjekte zusammengesetzt (z. B. „Moskva / Vladivostok“) | 12 | angepasst (v2 „Kandidaten verworfen“ präzisiert) |
| 62 | ohne Entscheidung, vorgeschlagen | `docs/data/reconciliation.json` `locations` ohne `decision`; 382 − 358 `counts.locationDecisions` | 24 | angepasst (M2, neu) |
| 63 | Summe | 334 + 12 + 12 + 24 | 382 | angepasst (M2, geht auf) |
| 64 | Darunter zwanzig Testdatei-Orte, etwa Paris, Praha, Wien | Vergleich `git show 0a50354:data/reconciliation/location-decisions.json` (20 Entscheidungen `decidedBy = repository-ground-truth-fixture`, `evidence = tests/wikidata_ground_truth.json`) mit b0c63ea (keine) | 20 | gestützt |
| 65 | Übrige vier ohne aktuellen Eintrag und Belegstelle | `docs/data/reconciliation.json` (București, La Tour d'Aigues, fehlkodiertes Rīga, Seoul-Variante); `knowledge/journal.md` Session 40 | 4 | nur in Claims, im Text nicht einzeln genannt |
| 66 | Vom 26. August bis zur Korrektur am 23. Oktober 2026 als von Agenten geprüft, mit veröffentlichten Links | `git log -S repository-ground-truth-fixture -- data/reconciliation/location-decisions.json`, eingeführt in 148a739 (2026-08-26), entfernt in 7994ccb (2026-10-23); `git show 0a50354:data/output/reconciliation/manifest.json` `publishableLocationLinks` 354 | 354 | v4 angepasst (Minor), Commit-Spanne durch Datumsangaben ersetzt |
| 67 | Entscheidung des Projektverantwortlichen vom 23.10.2026, Entscheidungen entfernt, Rückgang 354 → 334 | Commit-Nachricht 7994ccb; `knowledge/data.md` Provenance; `knowledge/status.md` Snapshot | 354 → 334 | angepasst, v4 Commit-Nennung aus dem Fließtext genommen |
| 68 | Sichtbar erst nach Bereitstellung | `git branch -a --contains 7994ccb` nur `main`; `git show 10966ab:data/output/reconciliation/manifest.json` `publishableLocationLinks` 354 | | v4 PRÜFEN-Kommentar auf LLM-Abschnitt und 334 erweitert (Blocker 1) |
| 69 | „Auch die Prüfregeln selbst brauchen Kontrolle.“ | Slogan | | entfernt (Review-Minor) |
| 70 | Belege zählen nur als ganze Wörter, seit „Bonnier“ als Beleg für Bonn galt | `knowledge/journal.md` Session 40; `knowledge/data.md` Reconciliation | | gestützt, v4 in den Satz zur Belegregel eingearbeitet (Minor) |

## Die gedruckten Bände (neu, M5)

| Nr. | Aussage | Quelle | Wert | Urteil |
|---|---|---|---|---|
| 71 | Zustände Hauptband 1991, Addendum I 1999, unveröffentlichtes Addendum II, Wiki | `knowledge/print-wiki-merge.md` erster Absatz | | angepasst |
| 72 | 1965 liegt dem Projekt nicht vor | `print-wiki-merge.md` („not available to the project“) | | angepasst |
| 73 | PDF-Dateien aus WordPerfect, digital erzeugte Textschicht, keine OCR | `knowledge/print-volumes.md` Technical properties („born-digital text layer … neither OCR nor HTR is required“, „produced in WordPerfect“) | 3 Dateien | angepasst |
| 74 | Hauptband-Datei ist späterer Arbeitsstand mit Einfügungen bis 2001 | `print-volumes.md` („insertions dated up to 2001 … a later state of the main volume, not the 1991 print“) | | angepasst |
| 75 | Unbekannt, was nur im Druck/Wiki/beiden steht | `print-wiki-merge.md`, `print-volumes.md` | | angepasst |
| 76 | Eigener Arbeitsstrang, Beziehung ohne Verschmelzung | `print-wiki-merge.md` Principles („Records are never merged“), `print-volumes.md` („separate strand“) | | angepasst |
| 77 | Ziel zusammengeführte Klawiter-Bibliographie, jede Aussage behält Quelle | `print-wiki-merge.md` | | angepasst |
| 78 | Bibliographischer Datensatz, keine Edition | `print-wiki-merge.md` („It is no scholarly edition, since its object is the bibliographic information, not the compiler's text and its transmission“) | | angepasst |
| 79 | Erste Befunde auf kleinen Stichproben, von einem einzelnen LLM-Agenten beurteilt und von keiner Person geprüft; Überschneidung teilweise, Bücher meist in beiden, Zeitschriftenbeiträge meist nur im Druck | `git show b0c63ea:knowledge/print-volumes.md` Z. 208 („Three overlap experiments on small seeded samples (2026-10-23, one agent reader, not human-checked …)“), Z. 211 (Overlap); `print-wiki-merge.md` Open questions | | v4 korrigiert (Minor), v3 „LLM-Agenten“ |
| 80 | Größere, von einer Person geprüfte Stichprobe soll zeigen, ob der Befund hält | `print-wiki-merge.md` („Answered by the human control of step 7“) | | angepasst |
| 81 | Rechte an Bänden und abgeleiteten Daten ungeklärt | `print-wiki-merge.md` Frame; `print-volumes.md` letzter Absatz | | gestützt |
| 82 | v2 „Derzeit werden … erschlossen und abgeglichen“ im Abschnitt Zugang | ersetzt durch den neuen Abschnitt | | entfernt |

## Fachliche Korrektur

| Nr. | Aussage | Quelle | Wert | Urteil |
|---|---|---|---|---|
| 83 | Das Projekt versteht Klawiter-Rescue als „epistemische“ Infrastruktur und übernimmt den Arbeitsbegriff aus DIA-XAI, „Gemeint ist hier …“ als eigene Bestimmung | zitierter Blogbeitrag Döring 2026, Volltext nicht gelesen; PRÜFEN-Kommentar | | Betreiber, v4 als Position formuliert (Major), Volltextlektüre offen |
| 84 | LLM-gestützte Transkriptionen aus dem Nachlass als zweites Beispiel | Blogbeitrag, DOI-Slot | | Betreiber |
| 85 | Anwendung schreibgeschützt, Bearbeitungsmodus nur lokal | `knowledge/frontend.md` („static localhost server for edit mode“, „joined on localhost by the Edit switch“) | | angepasst (M7, v2 „Lokal geöffnet zeigt sie Fachpersonen …“) |
| 86 | Bestätigen, korrigieren, ergänzen von Verlag, Ort, Übersetzer, Seitenzahl, Wikidata bestätigen/verwerfen/offenlassen | `knowledge/frontend.md`; `knowledge/data.md` Correction Protocol; `docs/js/edit.js` | | gestützt |
| 87 | Freigegebene Korrekturen als Änderungsdateien, Herkunftsangabe fachliche Korrektur | `data/corrections/README.md`; `docs/js/detail.js` (`editor` → „Expert curated“) | | gestützt |
| 88 | Freigegebene Korrekturen liegen nicht vor, Weitergabe in alle Exporte offen | `git ls-tree b0c63ea data/corrections/` (nur README.md); `knowledge/status.md` P1 provenance | 0 | gestützt |
| 89 | Tests laufen bei jeder ausgelieferten Änderung | `knowledge/status.md` Z. 59 (Tests workflow je ausgeliefertem Commit) | | v4 in den Abschnitt zur Entstehung verschoben und präzisiert, siehe Nr. 102 (Minor) |
| 90 | Fachliche Prüfung nur nach Pipeline- und Agentenergebnissen vorgesehen und noch nicht erfolgt; früheres Eingreifen offen | `git ls-tree b0c63ea data/corrections/` (nur README.md); `knowledge/status.md` (Arbeitsblatt-Fälle 1–4 „decided by the main instance after delegation“, Fall 5 und Partner-Abnahme am 23.09. zurückgezogen) | | v4 korrigiert (Blocker 2), Wortlaut aus dem Review |
| 91 | Befunde per E-Mail an [KONTAKT] | Review M7; Platzhalter, keine Adresse | | Betreiber |

## Zugang und Schluss

| Nr. | Aussage | Quelle | Wert | Urteil |
|---|---|---|---|---|
| 92 | Filter Zeitraum, Sprache, Ort, Art des Eintrags, Prüfstatus | `docs/js/facets.js` (type, language, period, location, review) | 5 Facetten | gestützt |
| 93 | BibTeX und RIS pro Publikation | `docs/js/detail.js` Z. 815–818 | | gestützt |
| 94 | Wiki-Text und Herkunft der Werte je Datensatz, Gesamtdownload | `docs/js/detail.js` `_buildReadContent`/`_sourceBlock`; `docs/index.html` `DataDownload` | | gestützt |
| 95 | Herausgeberschaft | `CITATION.cff` `preferred-citation.editors` vs. `knowledge/about.md` Responsibilities | | Betreiber (Slot, OPERATOR-Kommentar) |
| 96 | MIT für Code, CC BY 4.0 für Daten und Dokumentation | `knowledge/about.md` Licenses | | gestützt |
| 97 | DIA-XAI als Early Career Grant der PLUS gefördert, jetzt direkt bei der DIA-XAI-Nennung | nicht im Repository | | Betreiber, v4 verschoben, OPERATOR-Kommentar zum Verhältnis von DIA-XAI und Klawiter-Rescue (Major) |
| 98 | Zitierzeile, Version 0.9 | `CITATION.cff` `preferred-citation`, `docs/data/klawiter.json` `_meta.version` = 0.9 | 0.9 | gestützt, Zitierform Betreiber (OPERATOR-Kommentar) |
| 99 | Literaturliste | Betreiberangaben, zwei DOI-Slots | | Betreiber |

## Neue Zeilen in v4

| Nr. | Aussage | Quelle bei b0c63ea | Wert | Urteil |
|---|---|---|---|---|
| 100 | Überschrift „Wie Pipeline und Anwendung entstanden sind“ statt „Warum die Rettung jetzt möglich ist“ | Review Major | | v4 angepasst |
| 101 | Zwei Prüfstufen der Pipeline verlangen unter anderem SHACL-Validierung, stabile Kennungen und bitgleichen Neuaufbau | `CLAUDE.md` Verification Duty (Gate 1, Gate 2); `data/output/reconciliation/manifest.json` `validation` (`shacl`, `deterministicRebuild` true); `knowledge/status.md` Z. 59 („117 compared deterministic data/vocabulary files reproduced byte-identically“) | | v4 neu (Major) |
| 102 | Standardsuite bis auf einen bekannten Fehler, semantische Diagnose mit 21 bekannten Abweichungen | `knowledge/status.md` Absatz zum 23. Oktober („the default suite passed with one known failure (the redirect-map count), and the semantic diagnostics kept the same 21 failures“) | 1 / 21 | v4 neu (Major, Minor) |
| 103 | Unabhängige LLM-Agenten lasen Code und Daten wiederholt und prüften gemeldete Fehler nach | `knowledge/status.md` (23.09. „four read-only reviews“; 23.10. Defekte, „that an independent agent confirmed, partly by reproduction“) | | v4 neu (Major) |
| 104 | Der Projektverantwortliche legte Arbeitsweise, Regeln und Freigaben fest und delegierte die meisten fachlichen Einzelentscheidungen widerruflich | `knowledge/status.md` (Entscheidungen vom 22. und 23.09. „taken under delegation and stay revisable“; Betreiberentscheidungen zu Release, Rechten und Testdatei); `knowledge/about.md` Responsibilities | | v4 neu (Major) |
| 105 | Werk-/Ausgabengraph für einen festgelegten Teil des Korpus, eine Ausgabe ist eine Veröffentlichung mit eigenem, genau bezeichnetem Abschnitt im Wiki-Text | `knowledge/data.md` Work/edition graph (`oa:Annotation` mit exaktem Quellblock, Start/End-Selektor und SHA-256); `CLAUDE.md` („ratified multi-edition corpus“) | | v4 neu (Major) |
| 106 | 448 Werke, 2.077 Ausgaben | `git show b0c63ea:data/output/editions/manifest.json` `counts.works`, `counts.editions` (auch `annotations` 2077) | 448 / 2077 | v4 neu (Major). Die 76 bestätigten Ausgaben (`confirmedEditions`) sind nicht genannt, weil der Erzeuger dieser Bestätigungen nicht geprüft wurde und die Zahl die offene Frage zu „bestätigt“ berühren würde |
| 107 | Fünf Verknüpfungen hat der Hauptagent unmittelbar entschieden, etwa Varna, Bloemfontein, Tyresö | `location-decisions.json` `decidedBy = main-instance`, `action = confirm` (Varna Q6506, Bloemfontein Q37701, Kaapstad (Capetown) Q5465, Tyresö Q113730, Kuwait Q35178) | 5 | v4 neu (Major) |
| 108 | Herkunft der 334 Links | 323 + 5 + 6 | 334 | v4 neu, geht auf |
| 109 | Drei Werke, darunter die Schachnovelle, mit dem Werkindex von Stefan Zweig Digital verknüpft | `git show b0c63ea:data/output/reconciliation/publishable-links.json` `works` (work/4916 Schachnovelle SZDWRK.39, work/54 Ungeduld des Herzens SZDWRK.133, work/56 Die Welt von Gestern SZDWRK.5); `manifest.json` `counts.publishableWorkLinks` | 3 | v4 neu (Major) |
| 110 | Diese Werkentscheidungen traf ein LLM-Agent auf Grundlage derselben früheren Prüfung | `data/reconciliation/work-decisions.json`, alle drei `decidedBy = independent-verification-agent`, `evidence` `location-low-score-review.json#work-page-…` | | v4 neu (Major) |
| 111 | Deploy-Vorbehalt, die verlinkte Anwendung zeigt bis zur Bereitstellung 354 Links und die alten LLM-Werte | `git show 10966ab:data/output/llm-enrichment-report.json` (282/249/322/35, `rejectedCachedValues` 24); `git show 10966ab:data/output/reconciliation/manifest.json` (354) | | v4 neu (Blocker 1), nur als PRÜFEN-Kommentar |
| 112 | „Automatisierte Tests prüfen jede ausgelieferte Änderung am Code“ im Abschnitt Fachliche Korrektur | ersetzt durch Nr. 102 | | v4 entfernt |
| 113 | „Für die übrigen Aussagen zeigen ihn erst Prototypen einer neuen Ansicht“ | Verweis auf `docs/lab` | | v4 entfernt (Minor) |
