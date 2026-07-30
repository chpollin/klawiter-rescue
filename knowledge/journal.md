---
title: Journal
aliases: [work diary, sessions]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: complete
version: 0.3
tags: [journal]
created: 2026-03-29
updated: 2026-07-30
---

# Journal

Work diary for the Klawiter Bibliography project. One compact entry per substantive session with the fields Runde (what kind of round), Geändert (what changed), Entschieden (what was decided), Offen (what stays open).

---

## 2026-07-30 — Session 24: Wartungsrunde, Drift-Abgleich knowledge gegen Artefakte, antrag-eval-Hooks

**Runde.** Wartungs- und Verifikationsrunde ohne Subagents, ausgelöst aus dem Antrags-Workspace, weil das Repository als Vorarbeit von Reviewern geöffnet wird.
**Geändert.** Testlauf verifiziert (403 grün, 10 skips, 74 abgewählt; `-m semantic` weiter 17 rot by design, deckungsgleich mit der dokumentierten Schranke). Drift zwischen knowledge und den committeten Artefakten bereinigt: Redirect-Auflösung 1.210 auf 1.224, gebrochene seeAlso-Referenzen 727 auf 619, Deutsch-plus-Übersetzer 111 auf 110, Feld-Coverage-Tabelle und Regex-Only-Spalte auf den Stand des ausgelieferten Laufs, Provenienz-Verteilung aus `klawiter.json` neu gerechnet, Sprachverteilung aus dem Quality-Report übernommen, `klawiter.jsonld` als 6.725 statt 6.296 Einträge, CSV-Spaltenzahlen (27/29), Regressions-Schwelle kritischer Felder 1pp statt 0,5pp, Testdatei-Tabelle um `test_inject_provenance.py` ergänzt und Zählungen nachgezogen, pytest-Aufrufe an die tatsächlichen `addopts` angepasst. Zwei Aussagen als überholt widerlegt und korrigiert: Location-Fix und Mojibake-Reparatur sind im ausgelieferten Datensatz enthalten (kein Datensatz trägt noch den Vor-Fix-Wert, Eintrag 804 ist repariert), und der geblankte Stub 2979 trägt seinen Titel bereits. Frontend-Dokument sagte CDN für FlexSearch, D3 und Google Fonts, tatsächlich ist alles unter `docs/vendor/` und `docs/fonts/` vendoriert. README um einen Abschnitt Provenance and Curation erweitert (Produktions-Provenienz je Feld, Verifikations-Provenienz mit `editor`-Label und Review-Block, Patch-v2-Korrekturhistorie als Audit-Trail). Tote Dokumentzeiger im Code auf die konsolidierten Dokumente umgebogen (`eil-editing.md`, `validation.md` in vier Skripten und `edit.js`). Drei Issue-Templates unter `.github/ISSUE_TEMPLATE/` für die geplanten Evaluations-Hooks angelegt (Vier-Tupel-Protokollexport, Provenienz-Export, Gold-Standard-Hook), Label `antrag-eval` im Remote angelegt.
**Entschieden.** Volatile Zahlen bleiben in den Wissensdokumenten stehen, wo sie einen Befund tragen, werden aber gegen die committeten Artefakte geführt; die Regex-Only-Spalte wird als Stufenwert des gleichen Laufs markiert, weil `data/intermediate/` gitignoriert und für Reviewer nicht nachrechenbar ist.
**Offen.** Bracket-Titel-Restzahl (33 gegen ~15 im selben Dokument) nicht auflösbar ohne Neulauf; `corrections-report.json` liegt in einer älteren Fassung ohne `old_value_mismatch`-Schlüssel und ist nicht git-getrackt; die Evaluations-Hooks sind als Templates beschrieben, nicht gebaut.

**Der eine nächste Schritt.** Unverändert die Sichtung von `data/output/edition-samples/REVIEW.md` durch die Editorin.

## 2026-07-18 — Session 23: Review-Fixes, knowledge-Konsolidierung, Gate-Entscheide, Stichproben-Gate (Forschungsleitstelle-Lane)

**Runde.** Umsetzungs- und Entscheidungsrunde mit dem Operator, orchestriert mit Subagents.
**Geändert.** Pipeline-Review-Fixes gelandet (Provenienz-Diff gegen Regex-Output statt Cache-Präsenz, atomare JSON-Writes, sichtbare SQL-Skips, Mojibake-Guard, plus Unit-Tests); Baseline auf den Juni-Datenstand nachgezogen; `klawiter:`-Vokabular maschinenlesbar publiziert (Turtle + JSON-LD); knowledge-Ordner von 16 auf 8 Dokumente konsolidiert (Ontologie in data, ADRs in pipeline/frontend, Exploration- und EIL-Spezifikation in frontend, Edition-Modell in production-readiness, Fehlerklassen in testing; HANDOFF, references, validation aufgelöst); CLAUDE.md und README von volatilen Quantitäten befreit; Gate-1-Stichproben-Gate ausgeführt (`pipeline/segment_editions.py`, 76 Ausgaben-Drafts, Blockabgrenzung 76/76 adversarial verifiziert, `data/output/edition-samples/REVIEW.md`).
**Entschieden.** Alle vier Operator-Gates (siehe [[production-readiness#operator-entscheide-2026-07-18]]): Gate 1 dekomponieren, Gate 2 Reconciliation voll in die Produktionsreife, Gate 3 Druck-Merge spätere Ausbaustufe, Gate 4 Patch-Export kanonisch mit Write-Back als späterer Komfortschicht. Journal künftig im Kompaktformat.
**Offen.** Editorin-Sichtung der Segmentierungs-Drafts samt Tiefenentscheidungen vor dem Vollauf; PROV-Schicht für `klawiter.jsonld`; llmprov-Nachbarschaftsprüfung; drei Kopfzeilen-Reinigungsfälle aus der Verifikation.

**Der eine nächste Schritt.** Sichtung von `data/output/edition-samples/REVIEW.md` durch die Editorin; bei Freigabe Vollauf der Segmentierung über alle als mehrfach identifizierten Seiten.

## 2026-07-18 — Session 22: Modellierungsrunde Werk/Ausgabe

**Runde.** Rein konzeptuelle Modellierungsrunde mit dem Operator, keine Implementierung, kein Pipeline-Lauf.
**Geändert.** Werk/Ausgabe-Modell der Multi-Edition-Seiten als Wissensdokument eingearbeitet, [[production-readiness#work-edition-extension]] Arbeitspaket 1 auf Zielmodell plus Segmentierung plus Verifikation umformuliert, Gate-Abschnitt um Entscheidungsgrundlage und Gate-Reihenfolge ergänzt, [[data#work-edition-extension]] um einen Verweisabschnitt erweitert.
**Entschieden.** Multi-Edition ist ein Ebenenfehler, kein Extraktionsfehler; die Wiki-Seite beschreibt ein Werk, die `'''[Jahr]:'''`-Blöcke Ausgaben, First-match-wins macht Verlag/Ort/Jahr systematisch unzuverlässig und Handkorrektur heilt das nicht (Bracket-Titel sind dasselbe Symptom). Zielmodell Werk/Ausgabe mit schema.org (`workExample`/`exampleOfWork`), FRBR/LRM und BIBFRAME konzeptuell, kein Ontologiewechsel; Evidenz je Ausgabe als W3C Web Annotation, Provenienz als PROV-O-Sidecar mit `_provenance` als abgeleiteter Frontend-Kurzform, Prüfschicht als SHACL plus EARL/DQV, publizierbares PROV-Profil `llmprov`; stabiles quellableitbares ID-Schema `klawiter:edition/{pageId}-{jahr}-{buchstabe}` als Vorbedingung, damit Neusegmentierung Editor-Patches und Zitierbarkeit nicht verwürfelt. Vorgehen über ein Editor-gesichtetes Stichproben-Gate vor Vollauf.
**Offen.** Die vier Operator-Gate-Fragen bleiben unverändert, Gate 1 ist Gate 2 und 3 vorgelagert; der Editorin vorzulegen sind Auflagen-Unterzeilen als eigene Knoten oder strukturierte Beschreibung und Sammelband-Vorkommen über `schema:isPartOf`; die Nachbarschaftsprüfung des `llmprov`-Profils steht aus.

## 2026-07-18 — Session 21: EIL-Editor Increments 2 und 3

**Runde.** Umsetzungsrunde nach Operator-Freigabe, gebaut wurde nur, was an keiner Gate-Frage hängt.
**Geändert.** Increment 2 Prüfhinweise je Eintrag, neuer Schritt `pipeline/build_triage.py` reduziert die committeten verify- und census-Reports auf `docs/data/triage.json` (`notInSource`, `detectable` mit Add-Kandidat, `census` für 2979), `edit.js` bündelt sie zu einer nach Signalklasse geordneten Hinweisliste mit Chip, Feldmarker und Edit-Sortierung. Increment 3 Quell-Evidenz je Feld, im Edit-Modus steht neben jedem der vier getrackten Felder der wertetragende Quelltextausschnitt whitespace-tolerant markiert, Mehrfachtreffer werden gezählt (macht Multi-Edition-Ambiguität am Feld sichtbar), Fallback auf den ganzen Quelltext. Verifikation dreischichtig (Python-Triage-Pin, JS-Logik-Pin, Browser auf localhost).
**Entschieden.** Bewusst keine Metrik, kein Score, ein Hinweis erlischt sobald das Feld adjudiziert ist; bis zur Kalibrierung ist die Klassenordnung die dokumentierte Prüfpriorität, kein empirisches Signal; `triage.json` wird aus committeten Reports gebaut und nach jedem Pipeline-Lauf regeneriert.
**Offen.** Increment 4 lokaler Write-Back und editierbarer Titel hängen an den Gate-Fragen; die Triage-Kalibrierung wartet auf die stratifizierte Feld-Stichprobe.

## 2026-07-18 — Session 20: Konzeptrunde, EQUALIS-Entfernung, knowledge-Refactor

**Runde.** Rein konzeptuelle Runde nach Operator-Entscheid, keine Implementierung, keine Pipeline-Läufe.
**Geändert.** EQUALIS als Evaluationsframework restlos aus dem knowledge-Bestand entfernt und überall auf die hermeneutisch-qualitative Rahmung umgestellt, die frühere Ratio-als-Erfolgsbeleg-Formulierung durch die Protokoll-Rahmung ersetzt (Metrik-Sektion in [[data#correction-protocol]] heißt jetzt Correction Protocol, Dokumentationsgrundlage statt Messinstrument); knowledge-Ordner nach der Promptotyping-Konvention refactoriert, `index.md` von volatilen Statuszahlen befreit und selbsttragend gemacht; Konzeptdokument `production-readiness.md` angelegt mit Ist-Stand, den zwei Loops, den Provenienz-Schichten regex/llm/missing als Verifikationsgrundlage, dem Gold-Standard als messbarem Baustein, sechs geordneten Arbeitspaketen und vier Operator-Gate-Fragen.
**Entschieden.** Bewertung ist hermeneutisch-qualitativ, messbarer Baustein allein der im Werkzeug verifizierte Gold Standard, die Ratio ist kein Erfolgsbeleg; kein knowledge-Dokument gelöscht oder zusammengeführt, weil keine echte Redundanz vorliegt; operativer Stand lebt nach Konvention außerhalb des Navigationsdokuments.
**Offen.** Die vier Gate-Fragen (Multi-Edition kuratieren oder zurückstellen, Reconciliation-Tiefe, Wiki-Druck-Merge im Scope, Modellweg im Auslieferungsstand); zusätzlich ob der knowledge-Frontmatter repo-weit auf den Promptotyping-Pflichtkern geliftet wird, in dieser Runde bewusst nicht angefasst.

## 2026-06-21 — Session 19: EIL-Editor Increment 1

**Runde.** Umsetzungsrunde nach Operator-Richtungsentscheid, Strang 2 (Experten-Editierschicht) statt weiterer Datentreue-Härtung.
**Geändert.** `docs/js/edit.js` von der dünnen v1-Demo auf das volle Increment-1-Modell gehoben, jede Feldinteraktion als Accept/Correct/Add typisiert (Unterscheidung über Provenance und Ausgangswert), jede Aktion trägt die volle v2-Edit-History-Form, Drei-Status-Review je Eintrag als Chip, Pending Edits in localStorage reload-fest, Save exportiert ein `patchVersion: 2`-Dokument für `apply_patches.py`; `detail.js` rendert editierbare Zelle, Aktions-Controls, Review-Chip und den vollen Quelltext als Beleg-Panel. Verifikation über einen Patch-Kontrakt-Pin (JS-Export gegen Python-Apply) und eine Browser-Sichtung auf localhost.
**Entschieden.** Stille Divergenz behoben, das Backend schrieb Provenance `editor`, das Frontend kannte nur `expert`, jetzt kanonisch `editor` mit `expert` als Alias; der deployende Push bleibt Operator-Gate, gebündelt mit dem M3-Daten-Publish, der Editor-Code ist localhost-only und für Besucher inert.
**Offen.** Increment 2 (kalibriertes Triage-Signal), Increment 3 (Roh-Wiki je Feld), Increment 4 (lokaler Write-back-Endpunkt).

---

## 2026-06-21 — Session 18: Location-Fix und Mojibake-Reparatur gelandet

**Runde.** Milestone-Runde, zwei Fixes gebaut, getestet, nach main gesichert, Milestone 3 gescopt und lokal als Vorschau verifiziert.
**Geändert.** Location-Fix in `extract_location` gelandet und über `measure_location_fix.py` deterministisch vermessen (443 geändert, 795 neu gewonnen, 0 verloren; 43 der 48 Weimar-Fälle auf den echten Quellort, 5 kopflos oder nicht gelistete Transliteration); Punkt-Trenner-Nachtrag verhinderte, dass ein Header-Fallback einen Verlagsnamen als Ort griff. Mojibake-Reparatur des Transliterations-Blocks neu als lauf-weises Redecode statt Zeilendekodierung, selbstvalidierend und idempotent (62.351 Läufe repariert, 0 selbst-abgelehnt, 0 Rest); der Empty-Content-Zweig zeigt Seite 2979 jetzt mit `page_title` "A unidade espiritual do mundo". Alle drei durch Unit-Tests gesichert, keine neue Roteinfärbung.
**Entschieden.** Nicht halbfertig committen, der Location-Fix koppelt an den Mojibake-Repair, weil Rest-Mojibake den Ort bei Klasse-3-Einträgen erreicht; kein Block-Whitelist-Guard für Mojibake, weil er 5 legitime Nicht-Latein-Reparaturen verworfen hätte; M3-Full-Run ist entkoppelt und rein ausführend, muss aber den committeten LLM-Cache wiederverwenden, weil die Gemini-API in der Umgebung ausfällt.
**Offen.** M3 ist lokal verifiziert (`m3-preview-report.json`, end-zu-end 0 Orte und 0 Titel verloren), aber unveröffentlicht; der Publish-Push wartet auf Operator-Freigabe, weil er live deployt.

## 2026-06-21 — Session 17: Record Census und EIL-Editing-Design

**Runde.** Portfolio-Runde mit zwei Strängen, Datenintegrität vom SQL bis ins Frontend verifizieren und die In-Tool-Editierschicht entwerfen.
**Geändert.** `pipeline/census.py` gebaut, reproduzierbare Record-Rekonziliation über drei Schichten, fünf Identitäten alle PASS (JSON-LD 1:1 mit Quelle, kein Verlust, keine Dublette, kein erfundener Datensatz); Editier-Design als Wissensdokument (drei getypte Aktionen, Unsicherheits-Oberfläche aus Provenance/verify/Census, Persistenz in drei Schichten, Korrektur-Protokoll, fünf Inkremente) mit expliziter DIA-XAI-Anbindung; Rückschreib- und Audit-Schicht `apply_patches.py` implementiert (Overlay nach inject_provenance, Provenance `editor`, Edit-History je Feld, idempotent, leerer Store ist No-Op). Addenda in der Runde: Frontend-Validierung mit vier bestätigten Feldfehler-Klassen; alle externen JS- und Font-Abhängigkeiten lokal ins Repo vendoriert; Weimar-Fix entworfen und vermessen.
**Entschieden.** Die 2979-Frage aus Session 1 abschließend geklärt, quellseitiger Verlust durch Blanking drei Minuten nach Anlage, kein Pipeline-Fehler; Census als drittes Verifikationswerkzeug neben verify.py und 06_validate.py für die Achse Record-Vollständigkeit; 2979 nicht eigenmächtig gefixt, zeigen-mit-Titel versus ausschließen ist editorisch; ein Datenrettungswerkzeug darf nicht von externer CDN-Erreichbarkeit abhängen (geteilter Browser-Cache verunreinigte die CORS-Header); der Weimar-Fix landet erst mit seinen drei Bereinigungs-Teilproblemen und der Mojibake-Reparatur gemeinsam.
**Offen.** Operator-Entscheidungen zu 2979 und zum Bau der Editier-Inkremente.

## 2026-06-12 — Session 16: Full-Codebase Refactoring (Multi-Agent)

**Runde.** Vier-Lane-Analyse mit parallelen Agents, dann zwei Implementierungswellen auf disjunkten Bereichen.
**Geändert.** Frontend entrümpelt (totes `explore-overview.js` und zwei unerreichbare Methoden entfernt, `utils.topN()` ersetzt vier identische Call-Sites, Netzwerk-Filter-Listener vereinheitlicht); verhaltensneutrale Pipeline-Bereinigung (`03c_normalize.py` an das Schrittmuster angeglichen, fehlende `publisher_normalize.json` angelegt, tote Importe entfernt, `EXTRACTED_FIELDS` zentralisiert); Tests refactoriert (`test_normalize_unit.py` vor der Berührung von 03c geschrieben, zwei stets-übersprungene Regressionstests aktiviert, `KNOWN_*` in `baseline-metrics.json` zentralisiert, `broken_see_also_refs` 727 auf 622 als echte Datenverbesserung geratcht); veraltete Zahlen dokumentweit vereinheitlicht und der Reconciliation-Widerspruch aufgelöst (LOD-Verlinkung erlaubt und implementiert, Werte erfinden verboten). Browser-Smoke-Test grün; `locationSameAs` als Wikidata-URI je Primärort emittiert; 22 nicht gematchte Orte in ein Review-Template triagiert.
**Entschieden.** Zahlen driften, weil sie in mehreren Stellen hartkodiert sind, daher eine Verantwortungsmatrix mit je einer Quelle; stets-übersprungene Tests sind schlechter als keine; bewusst nicht getan wurden Mojibake-Regex-Konsolidierung, Sprachlisten-Dedup und SQL-Parser-Vereinheitlichung, weil ohne Pipeline-Neulauf nicht beweisbar verhaltensneutral.
**Offen.** EIL-Verifikations-Workflow als nächstes Arbeitspaket; Editor-Review der nicht gematchten Orte; `publisher_normalize.json` über den Editor-Loop mit echten Varianten füllen.

---

## 2026-04-12 — Session 15: Geography, Timeline-Modi, Normalisierung, Wikidata

**Runde.** Umsetzungsrunde Exploration und Datenqualität (fasst die zwei Session-15-Einträge des Tages zusammen).
**Geändert.** Geography-View mit orthographischem Globus und Flachkarten-Toggle plus semantischem Zoom (Länder- zu Städte-Bubbles); Wikidata-Reconciliation über `reconcile_locations.py` (360/382 gematcht, `locations.json` um Q-IDs und Ländercodes angereichert); drei Timeline-Modi Bars/Sparklines/Ranks statt Stream, globaler Provenance-Toggle, hash-basierte URL-State-Persistenz; Pipeline-Schritt 03c Normalisierung mit auditierbaren externen Mapping-Tabellen (Ortsvarianten, Verlags-Müllabweisung, Übersetzer-Bereinigung, pageCount-Ausreißer); alle 8 Felder auf Normalisierungskandidaten profiliert, Publisher als größtes Restproblem identifiziert (1.316 Singletons erfordern Handreview).
**Entschieden.** Ländercodes fehlten ganz und machten den semantischen Zoom zur leeren Hülle, Reconciliation löste das und lieferte LOD-Q-IDs als Bonus; Stream visuell schwach, weil curveBasis diskrete Daten glättet und stackOffsetWiggle die Nulllinie entfernt, Bars/Sparklines/Ranks bedienen die drei Forschungsfragen besser; Normalisierung als eigener Schritt hält Extraktion und Bereinigung trennbar und verletzt das Data-Integrity-Prinzip nicht; Publisher-Coverage-Rückgang 55,5 auf 52,2 Prozent ist korrekt, Müll entfernt statt valider Verlage.
**Offen.** Neue Features im Browser testen (Sparklines, Ranks, Globus, semantischer Zoom); Publisher-Clustering per Handreview; Sprache für Film/Symposium/Translation; seeAlso-Auflösung; `locationSameAs` in den JSON-LD-Output; Multi-Edition-Dekomposition.

---

## 2026-04-12 — Session 14f: Timeline-Redesign

**Runde.** Umsetzungsrunde Timeline-Neubau.
**Geändert.** Stacked Area zu Stacked Bars (diskrete bibliografische Zählungen je Jahr statt interpolierter Kurven), Layer-Toggle nach Sprache oder Typ, Provenance-Overlay je Jahr, semantischer Zoom über die Brush-Extent, fünf biografische Annotationen mit Kollisionsvermeidung, Brush-Cross-View-Events für Geography und Connections; Overview-Modus samt totem Code entfernt, drei Modi verbleiben.
**Entschieden.** Stacked Area war falsch für diskrete Zähldaten, Bars stellen sie ehrlich dar; Overview war redundant, die Timeline mit Layer-Toggle und Zoom deckt es mit besserer Interaktion ab; das Provenance-Overlay wirkt als Developer-in-the-Loop-Werkzeug, weil es zeigt, wo die Datenqualität über die Zeit variiert.
**Offen.** Weitere Modi Sparklines und Ranks; Layer-Toggle und Provenance-Overlay im Browser testen.

---

## 2026-04-12 — Session 14: Semantic Testing, Extraktionsfixes, Pipeline-Grenze

**Runde.** Umsetzungs- und Analyserunde Datentreue.
**Geändert.** `_provenance`-Block und kompakte Datenverifikation ins Frontend gebracht; 10 Einträge gegen das Live-Wiki verglichen (23 Prozent der Felder falsch); Semantic-Testing-Schicht angelegt (`test_semantic.py`, `test_heuristic.py`, Ground Truth); fünf Extraktionsfixes, der Titel-Fallback auf `page_title` mit der höchsten Wirkung (1.368 Section-Header auf 0), plus pageCount- und Publisher-Bereinigung und ein Encoding-Guard.
**Entschieden.** Die Pipeline ist an der natürlichen Grenze der Regex-Extraktion, weitere Fixes verschieben Fehler (Wert A zu Wert B) statt sie zu lösen; die 427 Multi-Edition-Seiten (6,8 Prozent) verursachen systematische Fehler, weil die Seite als Container mehrerer Publikationen als ein flacher Eintrag behandelt wird; `page_title` ist zuverlässiger als extrahierte Titel; Semantic-Tests sind die wertvollste Ergänzung, weil sie das Falsche quantifizieren und Regressionen verhindern.
**Offen.** Ground Truth von 10 auf 30+ stratifiziert erweitern; Frontend systematisch durchsehen; LLM-basierte Edition-Block-Segmentierung erwägen; WCAG-2.1-AA-Audit und Performance-Messung.

---

## 2026-04-12 — Session 12: JSON-LD-Validierung, Playground, Projekt-Audit

**Runde.** Umsetzungs- und Audit-Runde JSON-LD und Codebasis.
**Geändert.** Data-Integrity-Prinzip in CLAUDE.md dokumentiert (LLM-Audit bestätigt 0 halluzinierte Werte über fünf Anti-Halluzinations-Schichten); JSON-LD-@context in fünf Punkten korrigiert und mit PyLD validiert (Expansion, Kompaktion, N-Quads bestehen); JSON-LD-Playground-Frontend gebaut; Projekt-Audit fand drei Bugs und mehrere Doku-Inkonsistenzen. Bugs behoben, darunter der kritische Falsch-Key in `06_validate.py`/`verify.py`, der still 0 Einträge verarbeitete, sowie vier verschiedene Jahres-Caps und drei divergierende `ABOUT_ZWEIG_TYPES`-Definitionen.
**Entschieden.** Stille Validierungsfehler sind die schlimmsten Bugs, weil der Fallback `[]` keinen Fehler meldet, Eingaben immer auf Nicht-Leere prüfen; mehrfach definierte Konstanten driften, die Pipeline ist die Quelle und das Frontend spiegelt; Dokumentation verfällt schneller als Code, automatisierte Grep-Checks auf bekannte Zahlen fingen das ab.
**Offen.** Nichts über die laufenden Datenqualitäts-Stränge hinaus benannt.

---

## 2026-04-12 — Session 11: Testing-Strategie überarbeitet

**Runde.** Umsetzungsrunde Teststrategie nach kritischem Audit der bestehenden 280 Tests.
**Geändert.** `knowledge/testing.md` mit ehrlicher Taxonomie angelegt; drei neue Datentest-Dateien über alle Einträge (`test_census.py` Vollständigkeit, `test_schema.py` Schema, `test_consistency.py` Kreuzfeld-Plausibilität); Regressions- und Real-Entry-Tests überarbeitet (kaputtes `test_year_range_sane` gefixt, Schwellen geschärft, stille Skip-Logik entfernt). Befunde als gebundene Bekannt-Fehler eingezogen (14 `__TOC__`-Titel, 6 Markup-Titel, 111 deutsche Übersetzer-FPs, 717 kaputte seeAlso-Refs, 10 Filme mit pageCount, Seite 2979 als Stub, die die Doku fälschlich als "missing" führte).
**Entschieden.** Funktionen testen ist nicht Daten testen, die 280 Unit-Tests bewiesen die Regex an Rosinenstrings, keiner fragte nach Vollständigkeit oder Feldwerten; Form-Korrektheit ist nicht Inhalts-Korrektheit, nur Kreuzfeld-Tests flaggen implausible Kombinationen; stille Test-Passes sind schlechter als keine Tests; die größte Lücke bleibt die semantische Genauigkeit, weil nur ein Bruchteil der Einträge auf Korrektheit geprüft wird.
**Offen.** Die 20 Markup-Titel in der Pipeline fixen; die 111 deutschen Übersetzer-FPs untersuchen; Real-Entry-Sample von 20 auf 50 erweitern; seeAlso-Matching verbessern.

---

## 2026-03-31 — Session 10: Frontend-Cleanup, Datenqualität, Regressionstests

**Runde.** Umsetzungs- und Analyserunde Frontend und Datenqualität.
**Geändert.** Frontend über 12 Dateien refactoriert (`COLORS` als einzige Farbquelle gegen den CSS/JS-Mismatch, ungenutzte Helfer verdrahtet, `esc()` per Regex ~10x schneller, SRI-Hashes, Event-Delegation, ARIA-Labels); Datenqualität in drei Untersuchungen vertieft (Titel-Präzision, Publisher-Lücke, fehlende System-Checks); Regressionstest-Infrastruktur angelegt (`baseline-metrics.json`, 18 Tests, CI-Erweiterung); Titel-Extraktion verbessert (`correct_fallback`-Status, zweiter Bold-Block vor page_title-Fallback, `__TOC__`-Entfernung).
**Entschieden.** Verifikation muss der Extraktionsmethodik entsprechen, verify.py prüfte blind "Wert im Rohtext" ohne den page_title-Fallback zu kennen und erzeugte 880 Phantom-FPs; nicht jede Coverage-Lücke ist ein Bug, die 44 Prozent Publisher-Lücke sind überwiegend strukturell (Anthologie-Gedichte, Zeitschriftenartikel ohne eigenständigen Verlag); Unit-Tests sind keine Regressionssicherheit, System-Baseline-Vergleich ist für Daten-Pipelines essenziell; Farbwerte driften ohne Build-Schritt, eine geteilte Konstantendatei ist die einfachste Abhilfe.
**Offen.** Pipeline mit den Titel-Verbesserungen neu laufen und Wirkung messen; M3.8 manuelle Validierung von 50+ Einträgen im Live-Frontend.

---

## 2026-03-29 — Session 9: Interaktive Explorationsschnittstelle und Refactoring

**Runde.** Umsetzungsrunde Exploration.
**Geändert.** Generisches Chart.js-Dashboard durch eine D3-v7-Exploration mit drei Modi ersetzt (Timeline mit Stacked Area und biografischen Annotationen, Overview mit vier verknüpften Small Multiples, Connections als Force-Graph der seeAlso-Referenzen mit ~496 aufgelösten Kanten) plus geteiltem Detail-Panel; UX- und Explorationsfixes; fünf Refactorings (BibTeX-Dedup, O(1)-titleMap, `countByField()`, generischer Wiki-Section-Extractor, Encoding-Utilities verschoben); Exploration-Design als Wissensdokument mit Forschungsfragen und DH-Referenzen.
**Entschieden.** Generische Dashboards bedienen akademische Forschung nicht, Forscher brauchen zweckgebaute Werkzeuge mit konkreten Forschungsfragen; D3 per CDN trägt statische Seiten gut und die Timeline erzählt sofort die Zweig-Rezeptionsgeschichte; seeAlso-Netze sind dünner als erwartet wegen unaufgelöster Titel-Referenzen; die ~500 "Unknown"-Sprach-Einträge dominierten die Timeline und wurden zu "Other" gefaltet.
**Offen.** M3.8 manuelle Validierung; Explore-Verfeinerung (echter Streamgraph-Offset, mobile Erfahrung).

---

## 2026-03-29 — Session 8: Deployment-Vorbereitung und Namespace-Fix

**Runde.** Umsetzungsrunde Deployment.
**Geändert.** Namespace-URI über 10 Dateien von `klawiter-rescue.github.io` auf `chpollin.github.io/klawiter-rescue` korrigiert, GitHub-Footer-Link von einem Fremd-User auf `chpollin` korrigiert, LICENSE als Dual-License und CITATION.cff angelegt, README um Live-URL und Lizenz ergänzt, JSON-LD und Frontend-JSON per Schritt 05/06 neu erzeugt; Tests grün.
**Entschieden.** Die URI war fälschlich als Organisations-Page gesetzt, das reale Deployment ist eine Projekt-Page unter dem Personen-Account, was @context-Auflösung und alle hartkodierten URLs betraf; der Footer-Link zeigte auf einen früheren Beitragenden.
**Offen.** M3.8 manuelle Validierung mit Wiki-Abgleich; M7-Rest Live-Deployment-Test, Zenodo-DOI, Ankündigung.

---

## 2026-03-29 — Session 7: Design-Alignment, Verbund-Navigation, EIL-Kurationsschnittstelle

**Runde.** Umsetzungsrunde Design und Kuration.
**Geändert.** GAMS-Farbpalette und Source-Serif/Sans-Typografie über die Verbund-Sites übernommen, geteilte Verbund-Navigationsleiste über drei Sites, SZD-Frontend ins Englische übersetzt und Dashboard CIDOC-CRM-orientiert umgebaut, Klawiter-Landing auf aufklappbare Kategoriegruppen mit Browse- und Explore-Pfaden; EIL-Kuration gebaut (`inject_provenance.py` difft Regex gegen LLM-Cache zu `_provenance` regex/llm/missing, `edit.js` als localhost-only Edit-Modus mit JSON-Patch-Export, Provenance-Badges, Validierungs-Workflow auf PRs).
**Entschieden.** Provenance-Tracking schafft Vertrauen, indem es die Extraktionsquelle sichtbar macht und "missing" die Aufmerksamkeit lenkt; localhost-only Editieren ist ein pragmatisches Sicherheitsmodell für eine statische Seite ohne Auth; geteilte Navigation über drei Pages-Deployments verlangt stabile URL-Struktur.
**Offen.** Nichts über die laufenden Stränge hinaus benannt.

---

## 2026-03-29 — Session 6: Knowledge-Base-Audit und Doku-Refactoring

**Runde.** Audit-Runde Dokumentation.
**Geändert.** Alle Vault-Dateien, README, CLAUDE.md und den Implementierungsplan gegen Code und Datenoutput geprüft, 18 sachliche Ungenauigkeiten gefunden und über alle Dateien behoben (Ontologie fälschlich "pending", 15 statt 16 Entry-Types, 6 statt 7 Stufen, 4 statt 9 MB, fehlende Sessions 4–5, SZD-Institution falsch), Plan-Konsolidierung mit korrigiertem Abhängigkeitsdiagramm.
**Entschieden.** Doku-Schuld akkumuliert schnell, drei Features shippten am selben Anlagetag ohne Doku-Update, die Docs waren intern konsistent aber kollektiv veraltet; Cross-Referenzierung zählt, isolierte Vault-Dateien ohne Wikilinks sind im Wissensgraphen unsichtbar; zwei Planungsdateien stiften Verwirrung und verlangen Disziplin.
**Offen.** Nichts benannt.

---

## 2026-03-29 — Session 5: Frontend-Inhaltsseiten und Datenqualitätsfixes

**Runde.** Umsetzungsrunde Inhaltsseiten und Datenqualität.
**Geändert.** Fünf Inhaltsseiten (About, Methodology, Help, Data Access, Imprint) mit Navigation und Footer-Spalte; Vokabular gegen den echten `@context` geprüft; Pipeline-Fixes (bare Jahre als Originaltitel abgewiesen 272 auf 0, Section-Header und ungepaarte Bold-Marker aus Titeln entfernt, `@container: @set` ergänzt); automatisierte Validierung aller ns0-Einträge fand und behob Übersetzer-Regex-Leck über Zeilenumbrüche (34 auf 0); Pipeline neu gelaufen, Tests grün.
**Entschieden.** Vokabular-Docs müssen gegen Code verifiziert werden, die Seite behauptete `sameAs` als genutzt, obwohl kein Eintrag es trug; Schema.org ist vollständiger als angenommen, `Play` und `Collection` existieren; Markup in Titeln hat einen langen Schwanz; `\s` in Regex-Zeichenklassen matcht Zeilenumbrüche, `[ \t]` beschränkt korrekt auf horizontalen Whitespace.
**Offen.** Nichts benannt.

---

## 2026-03-29 — Session 4: Frontend-Redesign und Schema.org-Vokabular

**Runde.** Umsetzungsrunde Frontend und Vokabular.
**Geändert.** Frontend an die SZD-Bildsprache angeglichen (eigenes CSS mit SZD-Palette, Serif/Sans-System, Vier-View-Architektur, acht aus dem Monolithen extrahierte JS-Module, aufklappbare Ergebniskarten, klickbare Charts, BibTeX/RIS-Export mit korrekter Autorenlogik, responsiv); Schema.org-plus-Dublin-Core-Vokabular in `vocabulary.py` implementiert (16 Entry-Types auf Schema.org-Typen, Standardfelder via Schema.org, `dcterms:bibliographicCitation`, `klawiter:`-Namespace, Stefan Zweig als `schema:Person` mit Wikidata-Link), `05_to_jsonld.py` darauf umgeschrieben, Vokabular-Namespace-Seite angelegt.
**Entschieden.** Der Kategorie-Portal-Ansatz trägt, MediaWiki-vertraute Nutzer navigieren per Kacheln wie erwartet, die Landing ist Orientierung kein Dashboard; aufklappbare Karten schlagen separate Detailseiten, weil sie Kontext halten; Dual-Type-Arrays sind elegant, `@type` mit Schema.org- und klawiter-Typ gibt Interoperabilität ohne Informationsverlust.
**Offen.** Nichts benannt.

---

## 2026-03-29 — Session 3: Test-Suite und LLM-as-a-Judge

**Runde.** Umsetzungsrunde Tests.
**Geändert.** Initiale Suite von 171 Tests gebaut, dann kritisch getrimmt (redundante Guard-Clause- und Whitelist-Tests entfernt, geschwächte Titel-Tests auf den echten Pipeline-Fluss gefixt); Real-Data-Tests über 20 handgelabelte Einträge mit fünf Extraktoren; LLM-as-a-Judge (`test_llm_judge.py`) mit Gemini und strukturiertem Pydantic-Output, das eine Baseline bekannter Grenzen etabliert (10 wrong, 13 missed); Pytest-Marker zur Trennung von schnellen und API-Tests.
**Entschieden.** Redundante Tests schaffen falsches Vertrauen, 171 Tests klangen viel, die Real-Data-Tests fanden mehr als alle Guard-Clause-Tests zusammen; LLM-as-a-Judge ist wirksam und fängt semantische Fehler, die Pattern-Tests nicht sehen; Fixture-Text-Trunkierung erzeugte sechs falsche Fehlschläge; LLM-Nondeterminismus wird über ein Known-Wrong-Set gehandhabt, das bei Neuem rot wird.
**Offen.** Nichts benannt.

---

## 2026-03-29 — Session 2: Pipeline-Qualitätssicherung und LLM-Enrichment

**Runde.** Umsetzungsrunde Verifikation und LLM.
**Geändert.** `verify.py` als Round-Trip-Verifikation gebaut (jedes Feld gegen Roh-Wiki, FP- und FN-Erkennung, breitere Patterns für Publisher und Übersetzer), Ergebnisse je Feld mit Coverage und Präzision berichtet; Schritt 03b `03b_llm_enrich.py` mit Gemini als Gap-Filler entworfen und gebaut (Pydantic-Schema, Merge-Regel füllt nur leere Felder und überschreibt Regex nie, Cache-Resume, Validierung); über ein 20-Einträge-Stratum getestet, 13/13 korrekt, 0 Halluzinationen, alle Negativtests bestanden.
**Entschieden.** Verifikations-Zirkularität, dieselben Regex-Patterns zur FN-Erkennung finden nichts, dafür braucht es breitere Heuristik oder LLM; das LLM ist per Prompt konservativ und liefert null für See-Referenzen, Filme und deutsche Originale; Encoding-Artefakte gehen unangetastet durch, weil Mojibake-Reparatur Schritt 02s Aufgabe ist.
**Offen.** Nichts benannt.

---

## 2026-03-29 — Session 1b: Rohdaten-Verifikation

**Runde.** Analyserunde, zwei parallele Agents verifizieren Rohquelle gegen Extraktionslogik.
**Geändert.** Nur Analyse, kein Code; BLOB-Dateigrößen in pipeline.md korrigiert.
**Entschieden.** Die Pipeline ist korrekt, alle 6.296 ns0-Seiten werden verarbeitet, 6.295 finden ihren Inhalt in den BLOBs; der eine fehlende Eintrag ist page_id 2979 (text_id 18046, portugiesische Ausgabe), ein Quelldatenproblem, weil der text_id in keinem BLOB liegt; die 429 Nicht-ns0-Seiten sind per Design ausgeschlossen, darunter 420 Kategorieseiten; die SQL-Dumps 02 und 03 werden korrekt ignoriert (leeres Schema, Systemmetadaten); nur die jeweils letzte Revision je Seite wird extrahiert.
**Offen.** Ob die 420 Kategorieseiten für reichere Beschreibungen extrahiert werden; ob die verworfenen historischen Revisionen je gebraucht werden; ob der fehlende portugiesische Eintrag über die Titelsuche im BLOB statt über den text_id recovert werden kann.

---

## 2026-03-29 — Session 1: Repository-Restrukturierung und Planung

**Runde.** Milestone-Runde, Gründung der aktuellen Projektstruktur.
**Geändert.** Repository restrukturiert (v2-Inhalte auf Root-Ebene promotet, `frontend` zu `docs` für Pages, `working` zu `data/raw`, Pfadreferenzen in allen sieben Skripten angepasst, alle Legacy-Dateien gelöscht, neue .gitignore); Knowledge-Base refactoriert (10 deutsche Dokumente in fokussierte englische konsolidiert, neue Ontologie- und Reconciliation-Dokumente, Wikilinks verifiziert); `plan.md` mit sieben Milestones und Abhängigkeitskette angelegt.
**Entschieden.** Duplizierte Pfaddefinitionen erschwerten die Restrukturierung, volle Konsolidierung zu config.py-Importen geplant; die Verifikation muss immer breiter sein als die Reparatur, der erste Encoding-Fix behauptete 0 Prozent Mojibake, prüfte aber nur sieben Muster, 9,1 Prozent blieben; veraltete CLAUDE.md ist schlechter als keine, weil aktiv irreführend; Windows-Case-Insensitivity und IDE-Filelocks als Fallstricke.
**Offen.** Manuelle Validierung gegen die Quelle (50-Einträge-Stichprobe, sollte früh geschehen); der eine fehlende Eintrag; Publisher-Extraktion bei 34,5 Prozent als schwächstes Feld mit drei Ansätzen; Übersetzer-FP-Trade-off und mögliche Confidence-Scores; nicht auflösende JSON-LD-Namespace-URI; SZD-Integration und Design-Abgleich; ungeklärte Datenlizenz; Performance-Messung auf Mobil; fehlende Content Negotiation auf Pages; fehlende FAIR-Bausteine (PID, Standardvokabular, Lizenz).
