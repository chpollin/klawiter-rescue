---
title: Production Readiness
aliases: [production-readiness, curation-tool, work packages, EIL production tool]
tags: [eil, dia-xai, plan, concept]
created: 2026-07-18
updated: 2026-07-18
---

# Production Readiness

Konzept für den Weg vom lauffähigen Prototyp zum produktionsreifen Expert-in-the-Loop-Kurationswerkzeug für das Fachpersonal am Literaturarchiv. Dieses Dokument ordnet den Ist-Stand, die tragende Architektur der zwei Loops und die offenen Arbeitspakete; es beschreibt keine Umsetzung und trifft keine offene fachliche Entscheidung, sondern stellt diese als Gate-Fragen an den Operator. Es ist das Vorwärts-Pendant zum Verlauf in [[journal]] und zur Zielarchitektur der Editierschicht in [[eil-editing]]. Die Evaluationsrahmung ist [[about#dia-xai-connection]].

## Ist-Stand

### Datenbasis

Die Datenrettung ist auf Record-Ebene abgeschlossen und reproduzierbar bewiesen. Der Census in [[data#record-census]] zeigt die verlustfreie Übernahme von der SQL-Quelle über das JSON-LD bis ins Frontend, mit fünf Rekonziliations-Checks. Die einzige Anomalie ist eine quellseitig geblankte Seite, vollständig charakterisiert und kein Pipeline-Fehler, siehe [[data#known-problems]]. Auf Feld-Ebene ist die Basis dagegen unsicher: für einen erheblichen Teil der Einträge sind Publisher und Translator fehlend oder LLM-abgeleitet, Titel fallen teils auf Seitenmetadaten zurück. Die Feld-Fehlerklassen und ihre Mechanismen stehen in [[validation]], die dominante systematische Klasse ist die Multi-Edition-Seite. Diese Feld-Unsicherheit ist der Gegenstand der Expert-Kuration, nicht ein Restfehler, den die Pipeline allein schließen kann.

Die Provenienz jedes Werts ist im Datenmodell markiert (`_provenance`, gesetzt von `inject_provenance.py`) als `regex`, `llm` oder `missing`. Diese Markierung ist die technische Grundlage der Verifikation, sie sagt dem Fachpersonal je Feld, wie sicher die Pipeline war.

### Frontend

Das statische Frontend ist live, autark (alle Bibliotheken und Schriften lokal vendoriert, kein externer Request beim Laden) und trägt Volltextsuche, Facetten, Explorationssichten und Export. Die Editierschicht `edit.js` ist localhost-gated und implementiert die Increments 1 bis 3 aus [[eil-editing]]: Inline-Editieren der vier provenienz-getrackten Felder, getypt als Accept, Correct oder Add, mit v2-Edit-History, Drei-Status-Review je Eintrag, Persistenz in `localStorage` und Save-Export eines Patch-v2-Dokuments, das `pipeline/apply_patches.py` liest; dazu die Prüfhinweise je Eintrag aus den vorhandenen Datensignalen (Provenienz-Schichten, verify.py-Flags, Census-Anomalie, gebündelt über `build_triage.py` und `docs/data/triage.json`) und die Quell-Evidenz neben jedem getrackten Feld, feldgenau wo ein Ausschnitt ableitbar ist, sonst der ganze Quelltext einklappbar. Der Frontend-Backend-Patch-Kontrakt ist durch einen Test gepinnt, ebenso das Triage-Artefakt und die Evidenz-Logik. Offen ist Increment 4 (lebender lokaler Write-Back-Endpunkt statt manuellem Patch-Datei-Schritt), gebunden an die Modellweg-Gate-Frage unten.

## Die zwei Loops

Das Werkzeug bedient zwei ineinandergreifende Kontrollschleifen, die auf verschiedenen Ebenen arbeiten. Die Unterscheidung ist in [[about#two-eil-roles]] eingeführt; hier steht, was Produktionsreife für jede der beiden bedeutet.

**Developer-in-the-Loop, Pipeline-Ebene.** Der DH-Developer liest Testergebnisse und aggregierte Datendiagnosen, erkennt systematische Fehler, implementiert Code-Fixes und führt die Pipeline neu aus. Ein Fix wirkt auf tausende Einträge gleichzeitig. Das Feedback-Signal sind Tests und Datenvisualisierungen. Produktionsreif heißt hier, dass die systematischen Fehlerklassen aus [[validation]] adressiert sind, damit ein Editor nicht denselben Maschinenfehler tausendfach von Hand nachbessert.

**Editor-in-the-Loop, Datenebene.** Das Fachpersonal prüft einzelne Einträge gegen den Rohtext, korrigiert oder ergänzt Felder und validiert Reconciliation-Vorschläge. Das Feedback-Signal ist Domänenwissen über Zweigs Werk und Editionsgeschichte. Der Output sind Einzelkorrekturen, die in der Aggregation den Gold Standard bilden. Produktionsreif heißt hier, dass die Editierschicht alle adjudizierbaren Felder trägt, den Rohtext als Evidenz danebenstellt und jede Korrektur dauerhaft und auditierbar sichert.

Die beiden Loops greifen ineinander. Korrigiert der Editor systematisch denselben Fehlertyp, ist das ein Signal an den Developer, die Pipeline zu verbessern. Löst der Developer die Multi-Edition-Dekomposition, sinkt der Korrekturaufwand des Editors. Der Editor-Loop ist der, den die qualitative Auswertung primär dokumentiert; der Developer-Loop ist die Voraussetzung dafür, dass die Daten in einem Zustand sind, in dem ein Editor produktiv arbeiten kann.

## Provenienz-Schichten als Verifikationsgrundlage

Jedes getrackte Feld trägt eine der drei Provenienz-Schichten, und die Schicht steuert, wie das Werkzeug die Aufmerksamkeit des Editors lenkt.

- `regex` ist regelbasiert extrahiert, hohe Precision. Stichprobenprüfung genügt.
- `llm` ist LLM-angereichert unter Anti-Halluzinations-Constraints, mittlere Sicherheit, nicht validiert. Erste Prüfpriorität.
- `missing` ist nicht extrahiert. Hier prüft der Editor, ob der Rohtext den Wert doch enthält, und ergänzt ihn per Add.

Nach einer Accept- oder Correct-Aktion wandert die Provenienz des Felds auf `editor`; das Badge sagt dann nicht mehr nur, wie die Maschine den Wert erzeugt hat, sondern dass ein Mensch ihn verifiziert hat. Diese Schichtung ist die Verifikationsgrundlage, weil sie dem Fachpersonal ohne Blindsuche zeigt, wo die Pipeline sicher war und wo nicht. Sie wird ergänzt durch die Verifikations-Flags aus `verify.py` (Wert nicht im Rohtext gefunden, oder Wert im Rohtext detektierbar aber im Output fehlend) und die Census-Anomalien, siehe [[eil-editing#the-uncertainty-surface]].

## Gold Standard als messbarer Baustein

Der messbare Baustein der Evaluation ist der im Werkzeug verifizierte Gold Standard, gegen den die Extraktionsqualität der Pipeline pro Feld beschrieben wird. Das folgt dem [[about#dia-xai-connection|Evaluationskonzept]]. Die Konstruktion läuft im Werkzeug: das Fachpersonal liest die Felder eines Eintrags gegen den angezeigten Rohtext und bestätigt oder korrigiert sie; ein so vollständig geprüfter Eintrag steht auf `approved` und geht in den Gold Standard ein. In der Aggregation wächst daraus die expert-geprüfte Referenz, an der die Feld-Extraktion beschreibbar wird. Das ist dieselbe Beziehung, die das Schwester-Werkzeug szd-htr zwischen menschlichen Freigaben und seiner CER-Baseline hat, die menschlichen Urteile sind die fachlich gesicherte Referenz, gegen die das Maschinen-Ergebnis beschrieben wird.

Die Verifikation ist selbst eine dokumentierte Expert-in-the-Loop-Arbeitsepisode und damit zugleich Material für die qualitative Ebene. Der Gold Standard ist kein Wirksamkeitsmaß des Workflows; er beschreibt die Qualität eines Artefakts gegen eine gesicherte Referenz.

## Korrektur-Protokoll als Dokumentationsgrundlage

Weil jede Accept-, Correct- und Add-Aktion mit Feld, Provenienz, Aktion und Eintragstyp geloggt wird, hinterlässt die Kuration als Nebenprodukt ein Protokoll der Korrektur-Episoden. Das Protokoll hält fest, was wann woran korrigiert wurde, mit welcher Ausgangs-Provenienz und mit welchem Ausgangs- und Zielwert. Es ist Dokumentationsgrundlage für die qualitative Auswertung, kein Messinstrument. Systematische Korrekturmuster sind Werkstattbefunde: korrigiert das Fachpersonal wiederholt dasselbe Feld auf demselben Eintragstyp, ist das ein Signal an den Developer-Loop. Aus dem Protokoll werden keine Wirksamkeits-Kennzahlen des Workflows abgeleitet, kein Score je Iteration und keine Interaktions-Ratio als Erfolgsbeleg. Das Protokoll-Format liegt in [[data#correction-protocol]], die Herkunft aus der Editier-Interaktion in [[eil-editing#correction-episodes-are-logged-not-instrumented]].

## Arbeitspakete

Geordnet nach Abhängigkeit. Die Reihenfolge ist eine Empfehlung der Lane, kein Operator-Beschluss; die eingebetteten Gate-Fragen markieren, wo eine fachliche Entscheidung vor der Umsetzung nötig ist.

1. **Multi-Edition-Dekomposition.** Die dominante systematische Feld-Fehlerklasse. Eine Wiki-Seite enthält mehrere Publikationen, die flache Extraktion zieht jedes Feld aus einem beliebigen Block. Regex ist am Limit, siehe [[pipeline#known-limitations--multi-edition-pages]]. Ansatz: LLM-gestützte Edition-Block-Segmentierung, die den Rohtext einer als mehrfach identifizierten Seite in separate Einträge dekomponiert. Zuerst, weil viele fehlende Publisher- und Location-Werte von diesen Seiten stammen und die Dekomposition den Editor-Korrekturaufwand an der Wurzel senkt.

2. **Redirect-Auflösung.** Ein Teil der Redirects lässt sich nicht auflösen, weil der Target-Title nicht exakt auf einen bestehenden Eintrag passt, siehe [[architecture#4-redirects-as-map-instead-of-resolved-entries]]. Arbeitspaket: die nicht aufgelösten Redirects im Werkzeug zur Editor-Prüfung vorlegen, aufgelöste eintragen, verbleibende mit Begründung als unauflösbar markieren.

3. **Kategorie-Seiten-Auswertung.** Die extrahierten MediaWiki-Kategorie-Seiten sind bisher ungenutzt. Potenzial: reichere Metadaten für Kategorisierung und thematische Cluster sowie strukturelle Hinweise für die Multi-Edition-Dekomposition. Auswertung als eigener Pipeline-Schritt, dessen Ergebnis in die Anreicherung fließt.

4. **Reconciliation-Vorbereitung.** Die Verknüpfung der offenen Einträge mit dem SZD-Werkindex und externen Normdaten (Wikidata, GND, VIAF, GeoNames) ist als zweiter Expert-in-the-Loop-Schritt angelegt, siehe [[data#wikidata-reconciliation]] und den Forschungsplan im Vault. Vorbereitung heißt hier: die Kandidaten-Extraktion und das Confidence-Ranking so aufbereiten, dass der Editor Verknüpfungsvorschläge validieren kann, mit eigener protokollierter Verifikations-Episode. Die eigentliche Reconciliation ist Forschungsaufgabe und über dieses Konzept hinaus.

5. **Wiki-Druck-Merge mit Feld-Provenienz.** Die Bibliographie liegt in zwei Fassungen vor, dem extrahierten Wiki-Korpus und einer gescannten Druckversion. Welche Information nur im Wiki, nur im Druck oder in beiden steht, ist nicht vorab bekannt und kann unterschiedlichen Redaktionsstand tragen. Arbeitspaket: Druck-Scans segmentieren, per OCR/HTR auf Einträge mappen, gegen die Wiki-Einträge alignieren, den Diff pro Feld als Provenienz-Datenstruktur ablegen (`Wiki` / `Druck` / `beide`) und die Reconstruction-Sicht im Frontend um diese drei Zustände samt Faksimile der Druckseite erweitern. Die Druck-PDFs liegen im SZD-Repository, siehe den Forschungsplan im Vault (Phase B0).

6. **Deployment mit Zitierbarkeit.** Live-Deployment verifizieren (Routen, Suche, Daten laden), Zenodo-Deposit für einen DOI erwägen, `CITATION.cff` pflegen, den Link von Stefan Zweig Digital zur Klawiter-Bibliographie setzen (Abstimmung mit dem Projektteam). Zitierbarkeit heißt, dass die gerettete und kuratierte Ressource stabil adressierbar und als Datenpublikation referenzierbar ist.

## Braucht den Operator

Diese fachlichen Entscheidungen sind vor der jeweiligen Umsetzung nötig und werden hier nicht selbst getroffen.

1. **Multi-Edition-Behandlung im Editor.** Die als mehrfach identifizierten Seiten im Werkzeug aktiv dekomponieren und kuratieren, oder markieren und zurückstellen? Diese Frage steht seit der Milestone-Runde offen (siehe [[HANDOFF]]) und entscheidet, ob Arbeitspaket 1 eine Pipeline- oder eine Editor-Aufgabe wird.

2. **Reconciliation-Tiefe für die Produktionsreife.** Gehört die Normdaten-Reconciliation (Arbeitspaket 4) in den produktionsreifen Auslieferungsstand des Werkzeugs, oder bleibt sie als nachgelagerte Forschungsaufgabe außerhalb der Produktionsreife? Das entscheidet über den Umfang der Editier-Oberfläche.

3. **Wiki-Druck-Merge im Scope.** Ist der Merge mit der Druckversion (Arbeitspaket 5) Teil der ersten Produktionsreife, oder eine spätere Ausbaustufe? Er bringt eine OCR/HTR-Kette und eine zweite Provenienz-Achse ins Werkzeug und ist der größte Einzelaufwand unter den Paketen.

4. **Modellweg im Auslieferungsstand.** Increment 4 (lebender lokaler Write-Back) und der lokale Modellweg neben dem Cloud-Modell sind angelegt, aber nicht gebaut. Sind beide Teil der Produktionsreife, oder reicht für die Auslieferung der Cloud-Weg mit dem Patch-Datei-Export als portabler Fallback?

## Related

- [[eil-editing]] — Zielarchitektur der Editierschicht, Lineage aus szd-htr, Build-Inkremente
- [[about#dia-xai-connection]] — Evaluationsrahmung: Gold Standard messbar, Protokoll qualitativ
- [[data#correction-protocol]] — Format des Korrektur-Protokolls
- [[validation]] — Feld-Fehlerklassen, auf denen die Arbeitspakete aufsetzen
- [[pipeline#known-limitations--multi-edition-pages]] — Multi-Edition-Grenze der Pipeline
- [[HANDOFF]] — operativer Stand und offene Operator-Entscheidung
