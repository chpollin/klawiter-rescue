---
title: Oberfläche und Kuration
aliases: [frontend, interface, EIL, curation tool]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: de
version: 1.0
tags: [frontend, eil, accessibility, export]
created: 2026-03-29
updated: 2026-08-21
authors: [Christopher Pollin]
related: [data, pipeline, testing, production-readiness]
---

# Oberfläche und Kuration

## Aufgabe

Die statische Anwendung unter `docs/` macht den geretteten Bestand recherchierbar und stellt eine lokale Expert-in-the-Loop-Kurationsoberfläche bereit. Sie benötigt keinen Build-Schritt und keinen Serverprozess außer einem statischen localhost-Server für den Editiermodus.

Die öffentliche Anwendung unterstützt Suche, Facetten, Zeitverlauf, Sprach- und Ortsauswertung, Netzwerkansichten, Detailseiten und Zitationsexporte. Die lokale Kurationsschicht ergänzt Fundstellen, Provenienz, Triage und versionierten Patch-Export.

## Architektur

`docs/index.html` lädt Vanilla-JavaScript-Module und lokalisierte Abhängigkeiten. Zentrale Verantwortlichkeiten sind:

| Modul | Aufgabe |
|---|---|
| `app.js` | Daten laden, Zustand initialisieren, Routen koordinieren |
| `state.js` | Filter-, Auswahl- und Ansichtsstatus |
| `search.js`, `filters.js` | Volltextsuche und Facetten |
| `detail.js` | Eintragsdetail, Provenienz und strittige Aussagen |
| `edit.js` | lokale Feld- und Reconciliation-Kuration |
| `export.js` | BibTeX-, RIS-, Einzel- und Gesamtexport |
| `timeline.js`, `locations.js`, `network.js` | explorative Visualisierungen |

Die Anwendung lädt `docs/data/klawiter.json`, `triage.json` und `reconciliation.json`. Fehlende Reconciliation-Daten führen nicht zu erfundenen Links; die betroffenen UI-Bereiche bleiben leer.

## Gestaltungs- und Zugänglichkeitsvertrag

Die Oberfläche verwendet die etablierte Stefan-Zweig-Digital-Palette, Source Serif 4 für Lesetext und Source Sans 3 für Navigation und Bedienung. CSS-Variablen sind die einzige Quelle für Farben und Abstände. Bibliotheken und Fonts liegen lokal.

Semantisches HTML, sichtbarer Tastaturfokus, beschriftete Formulare, ARIA-Labels für ikonische Steuerelemente, ausreichende Kontraste und reduzierte Bewegung bilden die Basis. Inhaltliche Zustände werden nie ausschließlich über Farbe vermittelt. Mobile Layouts bewahren Suche, Filter und Detailinformationen ohne horizontales Scrollen.

## Rechercheansichten

- Die Übersicht zeigt Umfang, zeitliche Verteilung, Sprachen, Typen und Orte.
- Die Eintragsliste kombiniert Textsuche, Facetten und Sortierung.
- Die Detailseite zeigt strukturierte Felder, vollständigen Quelltext, Provenienz, verwandte Einträge, bestätigte Normdatenlinks und getrennte strittige Claims.
- Zeit-, Karten- und Netzansichten leiten ihre Daten aus derselben gefilterten Record-Menge ab.

Weiterleitungen erscheinen nicht als eigene Suchtreffer. Eine Map mit 1.310 auflösbaren Namen leitet Suchanfragen und Querverweise zum kanonischen Eintrag.

## EIL Curation Interface

Der Editiermodus ist ausschließlich auf `localhost` aktiv. Er bearbeitet Verlag, Publikationsort, Übersetzer und Seitenzahl. Jede Aktion ist typisiert:

- `accept` bestätigt einen vorhandenen Wert;
- `correct` ersetzt einen Wert und bewahrt den Vorgänger;
- `add` ergänzt einen zuvor leeren Wert.

Für jede Aktion zeigt die Oberfläche die belegbare Textstelle oder den vollständigen Quelltext. Triage-Hinweise priorisieren Round-Trip-Abweichungen, fehlende oder modellgestützte Provenienz sowie Census-Anomalien. Laufende Änderungen bleiben bis zum Export in `localStorage`.

Die Reconciliation-Kuration bietet `confirm`, `correct`, `reject` und `unresolved`. Kandidaten bleiben Vorschläge. `unresolved` hält konkurrierende Deutungen als offenen Claim fest. Der kombinierte Export verwendet `patchVersion: 2` und `reconciliationPatchVersion: 1`.

## Darstellung strittiger Aussagen

Bestätigte Beziehungen und strittige Aussagen werden getrennt gerendert. Ein offener Ortsclaim zeigt Quellenwert, Kandidaten, Entscheidungsgeschichte und offenen Status. Der Adaptionsfall auf Seite 4916 zeigt beide Werkdeutungen, Quellenkennung und Reviews.

Die UI erzeugt aus einem strittigen Kandidaten keinen klickbaren bestätigten Normdatenlink. Kennzahlen zählen ausschließlich publizierbare Beziehungen. Die Anzahl offener Claims wird getrennt ausgewiesen.

## Export

- BibTeX und RIS dienen der Zitationsweitergabe der flachen Records.
- Der JSON-LD-Einzelexport ergänzt vorhandene Editionsclaims als eigene Graphknoten.
- Der Gesamtexport enthält strittige Editions- und Normdatenclaims zusätzlich zu den bestätigten Beziehungen.
- Die kanonischen vollständigen Graphen bleiben `data/output/editions/work-editions.jsonld` und die Gate-2-Artefakte unter `data/output/reconciliation/`.

Ein Claim mit Prädikat `schema:exampleOfWork` wird exportiert, ohne gleichzeitig die entsprechende bestätigte Beziehung am Editionsknoten zu setzen.

## Validierung

Node-Tests prüfen Fundstellenlogik, Triage-Reihenfolge, Reconciliation-Lookup, stabilen Patch-Export und die Trennung strittiger Claims. `node --check` validiert jedes Modul syntaktisch. Die Python-Suite prüft die erzeugten Datenverträge und ruft die Node-Tests über die gemeinsame Testbrücke auf.

Ein lokaler Smoke-Test kann mit einem statischen Server im Repository-Root erfolgen:

```bash
python -m http.server 8000
```

Die Anwendung ist danach unter `http://localhost:8000/docs/` erreichbar; nur dort ist die Kurationsoberfläche aktiv.

## Deployment und Grenzen

GitHub Pages veröffentlicht den Inhalt von `docs/`. Die Anwendung führt keine Live-Rückschreibung aus. Exporte werden lokal heruntergeladen und anschließend als geprüfte Repository-Patches integriert.

Die flache Detailseite kann editionenspezifische Felder auf Mehrfachausgabenseiten nicht vollständig trennen. Der Editionsgraph und seine Queue bleiben für diese Fälle maßgeblich. Titelbearbeitung und institutionelle Werkentscheidungen gehören nicht zum aktuellen lokalen Editor.
