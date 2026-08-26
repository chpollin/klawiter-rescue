---
title: Projektkontext
aliases: [about, project context, klawiter, provenance]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: de
version: 1.0
tags: [project, context, provenance]
created: 2026-03-29
updated: 2026-08-21
authors: [Christopher Pollin]
related: [data, pipeline, frontend, testing, production-readiness]
---

# Projektkontext

## Gegenstand und Herkunft

Randolph J. Klawiter erarbeitete an der University of Notre Dame eine internationale Stefan-Zweig-Bibliographie. Der überlieferte MediaWiki-Bestand enthält Erstausgaben, Übersetzungen, Sekundärliteratur, Verfilmungen, Korrespondenz und weitere Publikationsformen in mehr als 40 Sprachen. Nach der Stilllegung des Wikis blieben ein SQL-Dump und acht binäre Textspeicher erhalten.

Das Projekt rekonstruiert daraus eine statische Rechercheoberfläche, einen vollständigen JSON-LD-Bestand und eine quellengebundene Kurationsschicht. Die Quelle bleibt unverändert. Alle Transformationen werden aus versioniertem Code, eingefrorenen Eingaben und nachvollziehbaren Entscheidungen erzeugt.

## Verantwortlichkeiten

- Randolph J. Klawiter ist Urheber der Bibliographie.
- Christopher Pollin verantwortet digitale Edition, Datenmodell, Software und Dokumentation.
- Stefan Zweig Digital liefert den fachlichen und institutionellen Bezug sowie den eingefrorenen SZD-Werkindex für Reconciliation-Kandidaten.
- Automatische und agentische Prüfungen liefern Evidenz. Institutionell inhaltverändernde Werkentscheidungen bleiben beim zuständigen Fachpersonal.

## Datenintegrität

Bibliographische Aussagen müssen in der MediaWiki-Quelle belegt sein. Quellenbedingte Leerstellen bleiben leer. Regelbasierte und eingefrorene LLM-Extraktion dürfen nur vorhandene Werte strukturieren. Jeder bearbeitete Feldwert trägt eine Provenienzklasse; Normdatenbeziehungen entstehen ausschließlich aus belegten `confirm`- oder `correct`-Entscheidungen.

Unsicherheit ist ein eigener Datenzustand. Strittige Aussagen besitzen stabile Identität, Fundstelle, konkurrierende Deutungen, Prüfverlauf und offenen Entscheidungsstatus. Sie gehören zum finalen Bestand, erzeugen jedoch keine bestätigte Beziehung.

## Forschungs- und Publikationsrahmen

Die methodische Leistung besteht in einer verlustfreien Datenrettung mit zwei gekoppelten Kontrollschleifen: systematische Pipelineverbesserung durch aggregierte Prüfungen und objektbezogene Fachkuratierung durch versionierte Patches. [[production-readiness]] beschreibt den ratifizierten Vertrag, [[testing]] die Reichweite der Nachweise.

Der auslieferbare Gegenstand umfasst Daten, Vokabular, Software, statische Oberfläche, Provenienz und Prüfartefakte. Ein eigenständiger Klawiter-Blogpost und eine neue Klawiter-Publikation gehören nicht zum Repository-Auftrag. Der Wiki-/Druck-Merge, externe Live-Rückschreibungen und institutionelle Werkentscheidungen bleiben spätere Optionen.

## Verbund und Gestaltung

Die Oberfläche ist mit Stefan Zweig Digital verbunden und verwendet die etablierte Farb- und Typografiesprache des Forschungsverbunds. Der technische Bestand bleibt eigenständig deploybar. Details stehen in [[frontend]].

## Lizenzen und Zitation

Der Code steht unter MIT. Dokumentation und strukturierte Edition stehen unter CC BY 4.0. `CITATION.cff` enthält die maschinenlesbaren Zitationsangaben; die bibliographische Quelle ist bei Nachnutzung ausdrücklich zu nennen.
