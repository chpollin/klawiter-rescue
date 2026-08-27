---
title: Daten und Modell
aliases: [data, dataset, data model, JSON-LD, work-edition extension]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: de
version: 1.1
tags: [data, model, provenance, reconciliation]
created: 2026-03-29
updated: 2026-08-27
authors: [Christopher Pollin]
related: [about, pipeline, frontend, testing, production-readiness]
---

# Daten und Modell

## Datenebenen

Das Repository bewahrt vier klar getrennte Ebenen:

1. `data/raw/` enthält den unveränderten MediaWiki-SQL-Dump und acht Textspeicher.
2. `data/intermediate/` enthält regenerierbare tabellarische Stufen und wird nicht versioniert.
3. `data/output/klawiter.jsonld` und `docs/data/klawiter.json` bilden die flache Kompatibilitätsschicht.
4. `data/output/editions/` und `data/output/reconciliation/` enthalten das strukturierte Editionsmodell, Reconciliation und Prüfartefakte.

Entscheidungseingaben liegen unter `data/reconciliation/`. Eingefrorene externe und modellgestützte Eingaben liegen unter `data/provenance/`. Diese Verzeichnisse sind Quellen des Produktionslaufs und keine temporären Ausgaben.

## Quellenumfang und bewusste Auslassungen

Die Pipeline verarbeitet ausschließlich die jeweils letzte Fassung jeder Seite. Der Dump enthält daneben rund 45.200 historische Revisionen, die bewusst ungenutzt bleiben; sie liegen vollständig in `data/raw/` und stehen einer späteren Auswertung offen. Die MediaWiki-Archivtabelle verzeichnet 207 gelöschte Seiten; ihre Triage (welche davon bibliographischen Wert trugen) ist nicht beauftragt und als offener Punkt registriert, siehe [[production-readiness]].

## Record Census

Der Census gleicht die gesamte Record-Kette ab:

| Ebene | Anzahl |
|---|---:|
| MediaWiki-Seiten | 6.725 |
| JSON-LD-Einträge | 6.725 |
| Weiterleitungen | 1.546 |
| Frontend-Einträge | 5.179 |
| Hauptnamensraum ohne Weiterleitungen | 4.751 |

Alle fünf Census-Invarianten bestehen. JSON-LD ist 1:1 zur Quelle, das Frontend entspricht JSON-LD abzüglich Weiterleitungen, und jeder sichtbare Eintrag besitzt einen Titel. Vier Seiten haben keinen gelieferten BLOB-Text; nur `page_id 2979` ist bibliographisch. Dieser quellenbedingt leere Datensatz bleibt als benannter Stub erhalten.

## Flaches Kompatibilitätsmodell

Die flache Schicht bewahrt die historische MediaWiki-Seite als Datensatz. Sie verwendet Schema.org, Dublin Core und das projektspezifische Präfix `klawiter:`. Typische Felder sind Titel, Jahr, Verlag, Publikationsort, Sprache, Übersetzer, Seitenzahl, Kategorien, Querverweise, Quellkennungen und Feldprovenienz.

Diese Darstellung bleibt für Suche, Zitation und bestehende Exporte erhalten. Bei Seiten mit mehreren Publikationsblöcken können Einzelwerte aus unterschiedlichen Ausgaben stammen. Das Editionsmodell ist für diese Seiten die strukturell präzisere Quelle.

## Werk-/Ausgabe-Modell

Gate 1 erfasst jede Hauptnamensraumseite mit mindestens zwei ratifizierten Ausgabe-Headern. Der aktuelle Bestand umfasst 443 Werke, 1.886 Ausgaben, 1.886 Web Annotations und sechs belegte Träger-Vorkommen.

- `schema:CreativeWork` bezeichnet das Werk der Quellseite.
- `schema:Book` bezeichnet den segmentierten Publikationsblock.
- `oa:Annotation` verbindet die Ausgabe mit dem exakten Quellausschnitt.
- `oa:TextPositionSelector` speichert Start, Ende und SHA-256 des Ausschnitts.
- `schema:PublicationVolume` bezeichnet ausschließlich ein quellenbelegtes Träger-Vorkommen.

Die Identifikatoren werden aus Quellseite, Jahr und stabiler Reihenfolge abgeleitet. Gleiche Eingaben erzeugen gleiche IDs, Selektoren und Graphknoten.

## Aussagezustände

Fachliche Beziehungen besitzen einen expliziten Status:

- `proposed`: deterministisch erzeugt und noch ungeprüft;
- `confirmed`: quellengebunden geprüft und bestätigt;
- `contested`: geprüft, weiterhin offen und mit konkurrierenden Deutungen erhalten.

Ein `klawiter:ContestedClaim` trägt eine stabile Claim-ID, Subjekt und Prädikat, exakte Quellenbelege, mindestens zwei Interpretationen, Review-Aktionen sowie `claimStatus = contested` und `decisionStatus = open`. Der Claim gehört zum finalen Datensatz. Sein Prädikat wird nicht zugleich als bestätigte Beziehung emittiert.

Der offene Adaptionsfall `klawiter:claim/work-binding/4916-2016-b` bewahrt die Deutung als Ausgabe der „Schachnovelle“ und die Deutung als eigenständiges Graphic-Novel-Adaptionswerk. Die Ausgabe selbst bleibt vollständig enthalten.

## Reconciliation

Gate 2 trennt Kandidaten, Entscheidungen, strittige Claims und publizierbare Links. Kandidaten entstehen für Orts-, Werk- sowie Übersetzer- und Verlagssubjekte (die Agent-Kandidaten aus dem eingefrorenen Wikidata-Abgleich `data/provenance/agent-reconciliation.json`, Schwelle fünf Vorkommen). Belegte Entscheidungen veröffentlichen die bestätigten Orts- und SZD-Werklinks; die aktuellen Zählungen stehen im Gate-2-Manifest `data/output/reconciliation/manifest.json`. Offene Ortsentscheidungen bleiben als strittige Claims erhalten.

`pipeline/05_to_jsonld.py` liest ausschließlich `publishable-links.json`. Kandidaten und offene Claims können in Oberfläche und Export sichtbar sein, erscheinen aber nicht als `schema:sameAs`. Die priorisierte Gate-2-Prüfliste umfasst alle offenen Orts-, Werk- und Agent-Fälle; ihre Größe steht im Manifest.

## Provenienz

Feldwerte in der flachen Frontend-Schicht tragen `regex`, `llm`, `missing` oder nach einer bestätigten Korrektur `editor`. Der Standardlauf verwendet den versionierten Cache `data/provenance/llm-enrichment-cache.json`; ein lokaler Arbeitscache beeinflusst den Produktionslauf nicht.

Gate 1 und Gate 2 speichern Eingabehashes, Codehashes, PROV-O-Aktivitäten, SHACL- beziehungsweise Vertragsprüfungen und EARL-Ergebnisse. Agentische Reviews benennen Eingabe, Reviewer, Ergebnis und Reconciliation. Unsichere Fälle bleiben in der Queue und werden nicht zu sicheren Aussagen geglättet.

## Korrekturprotokoll

Die Oberfläche exportiert ein versioniertes Kurationsdokument. Feldkorrekturen bewahren den vorherigen Maschinenwert im `edit_history`; Reconciliation-Entscheidungen bewahren ersetzte Entscheidungen in einer `supersedes`-Kette. Der Browser schreibt nicht direkt in das Repository.

Freigegebene Patches liegen unter `data/corrections/` und werden bei jedem Lauf erneut angewendet. `confirm` und `correct` erzeugen publizierbare Beziehungen. `reject` verwirft den geprüften Kandidaten. `unresolved` erzeugt oder aktualisiert einen offenen Claim.

## Qualitätsgrenzen

Die aktuellen Feldabdeckungen stehen ausschließlich in `data/output/quality-report.json`. Die wichtigsten bekannten Grenzen sind:

- 1.810 Editionssegmente bleiben Vorschläge; 75 Segmente sind agentisch bestätigt und eine Bindung ist strittig.
- Die verbleibenden nicht auflösbaren `seeAlso`-Referenzen sind echte Rotlinks auf nie angelegte Seiten; die Weiterleitungskarte enthält zusätzlich die Seitentitel-Aliasse aus Stufe 05. Die eingefrorenen Zählungen stehen in `.github/baseline-metrics.json` (`known_issues`).
- Die flache Schicht kann auf 443 Mehrfachausgabenseiten Werte verschiedener Ausgaben kombinieren.
- Fehlende bibliographische Werte können quellenbedingt sein und werden nicht erfunden.
- Der semantische Ground-Truth-Satz ist klein und misst keine corpusweite Fehlerrate.

Die genaue Testreichweite und alle bekannten Grenzwerte stehen in [[testing]].

## Kanonische Artefakte

| Artefakt | Funktion |
|---|---|
| `data/output/klawiter.jsonld` | vollständige flache JSON-LD-Schicht |
| `docs/data/klawiter.json` | Frontend-Daten mit Feldprovenienz |
| `data/output/editions/work-editions.jsonld` | Werk-/Ausgabe-Graph und Editionsclaims |
| `data/output/editions/review-queue.json` | priorisierte Editionsprüfung |
| `data/output/reconciliation/candidates.json` | Normdatenkandidaten |
| `data/output/reconciliation/decisions.json` | belegte Reconciliation-Entscheidungen |
| `data/output/reconciliation/contested-claims.json` | offene Normdatenclaims |
| `data/output/reconciliation/publishable-links.json` | bestätigte öffentliche Beziehungen |
| `docs/data/reconciliation.json` | deterministische UI-Projektion |
