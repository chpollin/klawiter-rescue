---
title: Production Readiness
aliases: [production-readiness, curation-tool, EIL production tool, edition-model, Werk-Ausgabe-Modell, work-edition split, PROV, SHACL]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: complete
language: de
version: 1.1
tags: [eil, dia-xai, concept, provenance]
created: 2026-07-18
updated: 2026-08-27
authors: [Christopher Pollin]
related: [about, data, pipeline, testing, frontend, journal]
---

# Production Readiness

Dieses Dokument beschreibt den ratifizierten und implementierten Produktionsstand. [[pipeline]] erklärt die Transformationen, [[data]] die Artefakte, [[frontend#EIL Curation Interface]] die Interaktion und [[testing]] die Qualitätsgrenzen. Der Verlauf der Entscheidungen steht in [[journal]].

## Publikationsrahmen

Der veröffentlichte Gegenstand besteht aus der digitalen Bibliographie, den JSON-LD-Daten, der Software, dem maschinenlesbaren Vokabular und den Provenienz- und Prüfartefakten. Ein eigenständiges Klawiter-Paper und ein separater Blogpost sind geschlossene Publikationslinien. Der Wiki-/Druck-Merge, externe Live-Rückschreibungen und institutionell inhaltverändernde Werkentscheidungen gehören nicht zu diesem Produktionsstand.

## Definition des terminalen Stands

Produktionsreife bedeutet in diesem Repository:

- die MediaWiki-Quelle lässt sich ohne Datenbankserver und ohne Netzwerkanfrage reproduzierbar verarbeiten;
- die vollständige Record-Kette von Quelle, JSON-LD und Frontend ist per Census abgeglichen;
- das relevante Mehrfachausgaben-Korpus besitzt eine vollständige Werk-/Ausgabe-Segmentierung mit exakten Quellenbezügen;
- Kandidaten, bestätigte Entscheidungen, strittige Aussagen und publizierte Beziehungen bleiben getrennt;
- automatische und agentische Prüfschritte besitzen Provenienz, Eingabehashes und maschinenlesbare Resultate;
- eine priorisierte Prüfliste bewahrt jeden ungeprüften oder offenen Fall;
- Korrekturen und neue Reconciliation-Entscheidungen lassen sich als versionierte Expert-in-the-Loop-Patches erneut anwenden;
- README, Einstiegsschicht und `knowledge/` beschreiben den ausführbaren Stand.

Eine externe Fachprüfung kann diesen Stand erweitern. Sie ist keine Voraussetzung für seine technische Reproduzierbarkeit.

## Zwei Kontrollschleifen

**Developer-in-the-Loop.** Aggregierte Tests und Datendiagnosen zeigen systematische Fehlerklassen. Eine Codeänderung wird gegen den gesamten Bestand, die Regressionsgrenzen und den Produktionslauf geprüft. Die Werk-/Ausgabe-Trennung löst den zentralen Ebenenfehler der früheren flachen Extraktion.

**Editor-in-the-Loop.** Fachpersonal prüft einzelne Felder, Ausgaben und Normdatenkandidaten gegen ihre Quellen. Der Browser exportiert typisierte Entscheidungen. Der Produktionslauf wendet freigegebene Patches erneut an und bewahrt Wertgeschichte oder Entscheidungssupersession.

Beide Schleifen verwenden dieselbe Evidenzkette. Maschinenwerte tragen `regex`, `llm` oder `missing`; geprüfte Feldwerte tragen `editor`. Ausgaben und Reconciliation-Aussagen unterscheiden `proposed`, `confirmed` und `contested`.

## Gate 1: Werk-/Ausgabe-Modell

### Auswahl und Identität

Eine Seite gehört zum Gate-1-Korpus, wenn sie im Hauptnamensraum mindestens zwei fett markierte Publikationsheader mit vierstelligem oder `ca.`-Jahr besitzt. Diese Regel wählt 443 Seiten vollständig und deterministisch aus.

Das Modell verwendet:

- `klawiter:work/{page_id}` für das Werk der Quellseite;
- `klawiter:edition/{page_id}-{year}-{suffix}` für jede Ausgabe in stabiler Quellreihenfolge;
- `klawiter:annotation/{page_id}-{year}-{suffix}` für die Web Annotation der Ausgabe;
- `klawiter:carrier/source-{page_id}-{year}-{suffix}` ausschließlich für ein belegtes Träger-Vorkommen.

Jede Ausgabe besitzt den unveränderten Header, `oa:start`, `oa:end` und den SHA-256 des ausgewählten Quellblocks. Derselbe Input erzeugt denselben Graphen und dieselben IDs.

### Ergebnis

Der aktuelle Graph enthält 443 Werke, 1.886 Ausgaben, 1.886 Annotationen und sechs Träger-Vorkommen. Die agentische Stichprobe umfasst 76 Fälle aus den Seiten 54, 56 und 4916. Zwei unabhängige Erstprüfungen wurden durch einen leistungsfähigeren, unabhängigen Verifikations-Agenten reconciliert. 75 Ausgaben sind innerhalb ihrer exakten Selektoren bestätigt. 1.810 weitere Ausgaben bleiben Vorschläge. Die vollständige Gate-1-Prüfliste enthält 317 aufgrund von Flags oder offenem Status priorisierte Fälle.

Die Test- und Entscheidungsartefakte liegen unter `data/output/edition-samples/`, `data/reconciliation/` und `data/output/editions/`.

### Strittige Werksbindung

`klawiter:edition/4916-2016-b` beschreibt „Die Schachnovelle nach Stefan Zweig“, eine Graphic-Novel-Adaption. Die Quelle belegt die Publikation, entscheidet jedoch nicht die institutionelle Werkidentität.

Der Fall bleibt als `klawiter:claim/work-binding/4916-2016-b` im finalen Graphen. Der Claim enthält:

- den exakten Selektor `[6866, 7104)` und den SHA-256 des Quellblocks;
- die konkurrierende Zuordnung zum Werk `klawiter:work/4916`;
- die konkurrierende Deutung als eigenständiger Kandidat `klawiter:work-candidate/4916-2016-b-adaptation`;
- die Urteile beider Erstprüfungen und der Reconciliation;
- `claimStatus = contested` und `decisionStatus = open`.

Die Ausgabe bleibt vollständig erhalten. Sie erscheint nicht in `schema:workExample` und trägt keine `schema:exampleOfWork`-Beziehung, solange die Fachentscheidung offen ist.

## Gate 2: Reconciliation

Gate 2 erzeugt für 382 Orts-, 443 Werk- sowie 101 Übersetzer- und Verlagssubjekte deterministische Kandidaten. Der eingefrorene SZD-Werkindex ist durch Quellpfad, Repository-Commit und SHA-256 provenienziert. Ortsvorschläge bewahren die Ergebnisse des früheren Reconciliation-Laufs und die unabhängige Prüfung als Kandidaten. Die Agent-Kandidaten stammen aus dem eingefrorenen Wikidata-Abgleich (`data/provenance/agent-reconciliation.json`, Schwelle fünf Vorkommen, 78 Subjekte mit mindestens einem Kandidaten); sie bilden einen neuen fail-closed-Prüfvorrat und publizieren nichts ohne belegte Entscheidung.

Entscheidungen liegen getrennt unter `data/reconciliation/`. Der aktuelle Stand umfasst 31 Ortsentscheidungen und drei Werkentscheidungen. Daraus entstehen 26 publizierbare Wikidata-Ortslinks und drei publizierbare SZD-Werklinks. `pipeline/05_to_jsonld.py` liest ausschließlich diese publizierbare Schicht.

Fünf Ortsentscheidungen bleiben offen. Jeder Fall besitzt einen stabilen `klawiter:ContestedClaim`, exakte Fundzeilen aus `04_classified.csv` mit Hash, konkurrierende Normdateninterpretationen, eine fail-closed-Alternative ohne Zuordnung und den Prüfverlauf. Offene Claims erzeugen kein `schema:sameAs`.

Die Gate-2-Prüfliste umfasst jeden Kandidaten ohne akzeptierte Entscheidung und jeden strittigen Fall über alle drei Subjektarten; ihre aktuelle Größe steht im Gate-2-Manifest. Der Umfang bezeichnet Prüfbedarf und keine Fehlerquote.

## Expert-in-the-Loop-Oberfläche

Der localhost-gebundene Editiermodus implementiert:

- Accept, Correct und Add für provenienzgetrackte Felder;
- Feldfundstellen oder den vollständigen Quelltext als Evidenz;
- Triage-Hinweise aus Provenienz, Round-Trip-Verifikation und Census;
- Ortskandidaten sowie Übersetzer- und Verlagskandidaten mit Confirm, Reject und Unresolved, wobei Unresolved in beiden Fällen auf den Fundstellen des Occurrence-Scans aufsitzt;
- subjektbezogene Entscheidungen mit ausgewiesener Reichweite, erreichbar am Eintrag und in der Kandidaten-Queue der Datenqualitäts-Werkbank (`#quality`, mit Tastatursteuerung);
- Persistenz der laufenden Sitzung in `localStorage`;
- einen kombinierten Export mit `patchVersion: 2` und `reconciliationPatchVersion: 1`.

Die öffentliche Detailansicht kennzeichnet strittige Normdatenzuordnungen. Für Seite 4916 zeigt sie den offenen Werkbindungs-Claim, beide Deutungen, den Prüfverlauf und die Quellenkennung. Der JSON-LD-Einzelexport übernimmt diesen Claim; der Gesamtexport enthält die strittigen Editions- und Normdatenclaims.

## Provenienz und Qualitätsnachweise

Gate 1 verwendet PROV-O für Quellkorpus, Software-Agent, Plan, Input-Hashes und erzeugte Knoten. SHACL prüft Werk, Ausgabe, Annotation, Träger, Claim, Interpretation, ReviewAction und Werkidentitätskandidat. EARL hält jedes automatische Prüfergebnis fest.

Gate 2 bewahrt die Eingabehashes für Editionsgraph, Ortsdaten, Review-Evidenz, Entscheidungsdateien, SZD-Index, klassifizierte Quelle und Kurationspatches. Sein Validator prüft deterministischen Neuaufbau, Entscheidungsseparation, Claim-Vollständigkeit, Eingabehashes und die Projektion in JSON-LD und Frontend. Die Qualitäts- und Census-Berichte ergänzen diese objektbezogenen Verträge.

## Ratifikationsgeschichte

### Operator-Entscheide (2026-07-18)

Die Entscheidungen vom 2026-07-18 wurden am 2026-07-19 ratifiziert:

1. Mehrfachausgabenseiten werden in Werk und Ausgabe dekomponiert.
2. Reconciliation gehört zum produktionsreifen Auslieferungsstand.
3. Der Wiki-/Druck-Merge bleibt eine spätere Ausbaustufe.
4. Der versionierte Patch-Export ist der kanonische Write-Back-Weg.

Am 2026-08-21 ersetzte das agentische Review die externe Stichprobe als Startbedingung. Zwei unabhängige Erstprüfungen und eine stärkere Reconciliation bilden die aktuelle Evidenz. Eine spätere externe Prüfung ist zusätzliche Validierung.

Ebenfalls am 2026-08-21 wurde entschieden, dass strittige Fälle Bestandteil der finalen Daten sind. Sie werden als offene Claims modelliert und bleiben von bestätigten Beziehungen unterscheidbar.

## Grenzen, offene Punkte und Operator Points

Die flache Kompatibilitätsschicht bleibt für Mehrfachausgabenseiten strukturell ungenau; der Gate-1-Graph ist dort die präzisere Darstellung. Die vollständigen Prüfvorräte (unbestätigte Ausgaben, Gate-2-Fälle über Orte, Werke, Übersetzer und Verlage) stehen in den Queues und Manifesten. Bekannte semantische Ground-Truth-Fehler stehen in [[testing]].

Registrierte offene Punkte, die den reproduzierbaren Produktionsstand nicht blockieren:

- Triage der 207 Seiten in der MediaWiki-Archivtabelle (nicht beauftragt; Entscheidung beim Operator).
- Cross-View-Brushing in den Explore-Ansichten (bewusst zurückgestellt; der Nutzen einer verknüpften Selektion über die Views steht in keinem Verhältnis zur Komplexität eines geteilten Selektionszustands, Wiederaufnahme nur auf Operator-Entscheid). Die übrigen Punkte der Kosmetikrunde (Sprach- und Richtungsattribute, Sortierung im URL-Hash, Inline-Handler in home und facets) sind umgesetzt.
- Abarbeitung des Übersetzer- und Verlags-Prüfvorrats als Kurationsaufgabe.
- Externe Fachprüfung als zusätzliche Validierung auf dem fertigen Werkzeug.
- Zwei Titel (Seiten 4775 und 5913) tragen ein verirrtes arabisches Diakritikum (U+0650) als Encoding-Rest; Kandidat für die Normalisierungsstufe, kosmetisch.

Operator Points: die institutionelle Werkidentität der Graphic-Novel-Adaption `klawiter:edition/4916-2016-b` (der vorhandene Claim sichert den Fall vollständig), die Abnahme der Version 1.0 und, nach der Abnahme, die Publikations- und Zitierform (Release-Tag, Zenodo/DOI).

## Evidenzorte

| Aussage | Kanonischer Nachweis |
|---|---|
| vollständiger Produktionslauf | `pipeline/run_pipeline.py` und finaler Audit unter `data/output/audits/` |
| Werk-/Ausgabe-Graph | `data/output/editions/work-editions.jsonld` |
| Gate-1-Vertrag | `data/schema/work-edition-shapes.ttl` und `data/output/editions/validation-report.json` |
| agentisches Sample-Review | `data/output/edition-samples/reviews/` |
| Reconciliation-Kandidaten und Entscheidungen | `data/output/reconciliation/` und `data/reconciliation/` |
| strittige Normdatenclaims | `data/output/reconciliation/contested-claims.json` |
| öffentlicher Link-Layer | `data/output/reconciliation/publishable-links.json` |
| Expert-in-the-Loop-Vertrag | `data/corrections/README.md` und [[frontend#EIL Curation Interface]] |
| Gesamtqualität | `data/output/quality-report.json`, Census- und Verifikationsbericht |
