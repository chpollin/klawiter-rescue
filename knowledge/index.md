---
title: Klawiter Bibliography
aliases: [MOC, map of content, index]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: de
version: 1.0
tags: [index]
created: 2026-04-12
updated: 2026-08-21
authors: [Christopher Pollin]
related: [about, data, pipeline, frontend, production-readiness, testing, journal]
---

# Klawiter Bibliography – Projektwissen

Diese Datei ist der Einstieg in das kanonische Projektwissen. Das Repository beschreibt hier langlebige Entscheidungen und den belegten Produktionsstand. Laufende Kennzahlen stammen aus `data/output/quality-report.json`, den Gate-Manifests, `.github/baseline-metrics.json` und der Testsuite.

## Dokumente

| Dokument | Zuständigkeit |
|---|---|
| [[about]] | Gegenstand, Herkunft, Verantwortlichkeiten und Publikationsrahmen |
| [[data]] | Datenebenen, Modell, Provenienz, Reconciliation und Grenzen |
| [[pipeline]] | ausführbare Transformation, Eingaben, Stufen und Wiederholbarkeit |
| [[frontend]] | statische Rechercheoberfläche und Expert-in-the-Loop-Kuration |
| [[production-readiness]] | ratifizierter Produktionsvertrag, Gate-Ergebnisse, offene Punkte und Operator Points |
| [[testing]] | Testschichten, Qualitätsnachweise und Aussagegrenzen |
| [[journal]] | chronologische Entscheidungen und abgeschlossene Arbeitssitzungen |

## Lesestrecken

- Wiedereinstieg: [[journal]] → [[production-readiness]] → `git status -sb`.
- Produktionslauf: [[pipeline]] → [[testing]] → [[data]].
- Datenmodell und strittige Aussagen: [[data]] → [[production-readiness]].
- Oberfläche und Kuration: [[frontend]] → [[data#Korrekturprotokoll]].
- Projektkontext: [[about]] → [[production-readiness]].

## Autorität und Pflege

`README.md` ist das ausführbare Benutzerhandbuch. `CLAUDE.md` ist die einzige repository-spezifische Agentenanweisung. Bei Widersprüchen haben Code, versionierte Entscheidungseingaben und erzeugte Prüfberichte Vorrang vor beschreibender Dokumentation. Historische Aussagen im [[journal]] bleiben als Verlauf erhalten und gelten nicht automatisch als aktueller Stand.
