---
title: Production Readiness
aliases: [production-readiness, curation-tool, work packages, EIL production tool, edition-model, Werk-Ausgabe-Modell, work-edition split, PROV, SHACL, llmprov]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: complete
language: de
version: 0.3
tags: [eil, dia-xai, plan, concept]
created: 2026-07-18
updated: 2026-07-18
authors: [Christopher Pollin]
related: [about, data, pipeline, testing, frontend]
---

# Production Readiness

Konzept für den Weg vom lauffähigen Prototyp zum produktionsreifen Expert-in-the-Loop-Kurationswerkzeug für das Fachpersonal am Literaturarchiv. Dieses Dokument ordnet den Ist-Stand, die tragende Architektur der zwei Loops, die offenen Arbeitspakete und die Gates mit ihrer Entscheidungsgrundlage. Es ist das Vorwärts-Pendant zum Verlauf in [[journal]]; die Zielarchitektur der Editierschicht steht in [[frontend#eil-curation-interface]], die Evaluationsrahmung in [[about#dia-xai-connection]].

## Ist-Stand

### Datenbasis

Die Datenrettung ist auf Record-Ebene abgeschlossen und reproduzierbar bewiesen. Der Census in [[data#record-census]] zeigt die verlustfreie Übernahme von der SQL-Quelle über das JSON-LD bis ins Frontend, mit fünf Rekonziliations-Checks. Die einzige Anomalie ist eine quellseitig geblankte Seite, vollständig charakterisiert und kein Pipeline-Fehler, siehe [[data#known-problems]]. Auf Feld-Ebene ist die Basis dagegen unsicher: für einen erheblichen Teil der Einträge sind Publisher und Translator fehlend oder LLM-abgeleitet, Titel fallen teils auf Seitenmetadaten zurück. Die Feld-Fehlerklassen und ihre Mechanismen stehen in [[testing#field-level-fidelity-findings]], die dominante systematische Klasse ist die Multi-Edition-Seite. Diese Feld-Unsicherheit ist der Gegenstand der Expert-Kuration, nicht ein Restfehler, den die Pipeline allein schließen kann.

Die Provenienz jedes Werts ist im Datenmodell markiert (`_provenance`, gesetzt von `inject_provenance.py`) als `regex`, `llm` oder `missing`. Diese Markierung ist die technische Grundlage der Verifikation, sie sagt dem Fachpersonal je Feld, wie sicher die Pipeline war.

### Frontend

Das statische Frontend ist live, autark (alle Bibliotheken und Schriften lokal vendoriert, kein externer Request beim Laden) und trägt Volltextsuche, Facetten, Explorationssichten und Export. Die Editierschicht `edit.js` ist localhost-gated und implementiert die Increments 1 bis 3 aus [[frontend#eil-curation-interface]]: Inline-Editieren der vier provenienz-getrackten Felder, getypt als Accept, Correct oder Add, mit v2-Edit-History, Drei-Status-Review je Eintrag, Persistenz in `localStorage` und Save-Export eines Patch-v2-Dokuments, das `pipeline/apply_patches.py` liest; dazu die Prüfhinweise je Eintrag aus den vorhandenen Datensignalen (Provenienz-Schichten, verify.py-Flags, Census-Anomalie, gebündelt über `build_triage.py` und `docs/data/triage.json`) und die Quell-Evidenz neben jedem getrackten Feld, feldgenau wo ein Ausschnitt ableitbar ist, sonst der ganze Quelltext einklappbar. Der Frontend-Backend-Patch-Kontrakt ist durch einen Test gepinnt, ebenso das Triage-Artefakt und die Evidenz-Logik. Der Increment-Stand steht in [[#eil-editing-increments]].

## Die zwei Loops

Das Werkzeug bedient zwei ineinandergreifende Kontrollschleifen, die auf verschiedenen Ebenen arbeiten. Die Unterscheidung ist in [[about#two-eil-roles]] eingeführt; hier steht, was Produktionsreife für jede der beiden bedeutet.

**Developer-in-the-Loop, Pipeline-Ebene.** Der DH-Developer liest Testergebnisse und aggregierte Datendiagnosen, erkennt systematische Fehler, implementiert Code-Fixes und führt die Pipeline neu aus. Ein Fix wirkt auf tausende Einträge gleichzeitig. Das Feedback-Signal sind Tests und Datenvisualisierungen. Produktionsreif heißt hier, dass die systematischen Fehlerklassen aus [[testing#field-level-fidelity-findings]] adressiert sind, damit ein Editor nicht denselben Maschinenfehler tausendfach von Hand nachbessert.

**Editor-in-the-Loop, Datenebene.** Das Fachpersonal prüft einzelne Einträge gegen den Rohtext, korrigiert oder ergänzt Felder und validiert Reconciliation-Vorschläge. Das Feedback-Signal ist Domänenwissen über Zweigs Werk und Editionsgeschichte. Der Output sind Einzelkorrekturen, die in der Aggregation den Gold Standard bilden. Produktionsreif heißt hier, dass die Editierschicht alle adjudizierbaren Felder trägt, den Rohtext als Evidenz danebenstellt und jede Korrektur dauerhaft und auditierbar sichert.

Die beiden Loops greifen ineinander. Korrigiert der Editor systematisch denselben Fehlertyp, ist das ein Signal an den Developer, die Pipeline zu verbessern. Löst der Developer die Multi-Edition-Dekomposition, sinkt der Korrekturaufwand des Editors. Der Editor-Loop ist der, den die qualitative Auswertung primär dokumentiert; der Developer-Loop ist die Voraussetzung dafür, dass die Daten in einem Zustand sind, in dem ein Editor produktiv arbeiten kann.

## Provenienz-Schichten als Verifikationsgrundlage

Jedes getrackte Feld trägt eine der drei Provenienz-Schichten, und die Schicht steuert, wie das Werkzeug die Aufmerksamkeit des Editors lenkt.

- `regex` ist regelbasiert extrahiert, hohe Precision. Stichprobenprüfung genügt.
- `llm` ist LLM-angereichert unter Anti-Halluzinations-Constraints, mittlere Sicherheit, nicht validiert. Erste Prüfpriorität.
- `missing` ist nicht extrahiert. Hier prüft der Editor, ob der Rohtext den Wert doch enthält, und ergänzt ihn per Add.

Nach einer Accept- oder Correct-Aktion wandert die Provenienz des Felds auf `editor`; das Badge sagt dann nicht mehr nur, wie die Maschine den Wert erzeugt hat, sondern dass ein Mensch ihn verifiziert hat. Diese Schichtung ist die Verifikationsgrundlage, weil sie dem Fachpersonal ohne Blindsuche zeigt, wo die Pipeline sicher war und wo nicht. Sie wird ergänzt durch die Verifikations-Flags aus `verify.py` (Wert nicht im Rohtext gefunden, oder Wert im Rohtext detektierbar aber im Output fehlend) und die Census-Anomalien, siehe [[frontend#the-uncertainty-surface]].

## Gold Standard als messbarer Baustein

Der messbare Baustein der Evaluation ist der im Werkzeug verifizierte Gold Standard, gegen den die Extraktionsqualität der Pipeline pro Feld beschrieben wird. Das folgt dem [[about#dia-xai-connection|Evaluationskonzept]]. Die Konstruktion läuft im Werkzeug: das Fachpersonal liest die Felder eines Eintrags gegen den angezeigten Rohtext und bestätigt oder korrigiert sie; ein so vollständig geprüfter Eintrag steht auf `approved` und geht in den Gold Standard ein. In der Aggregation wächst daraus die expert-geprüfte Referenz, an der die Feld-Extraktion beschreibbar wird. Das ist dieselbe Beziehung, die das Schwester-Werkzeug szd-htr zwischen menschlichen Freigaben und seiner CER-Baseline hat, die menschlichen Urteile sind die fachlich gesicherte Referenz, gegen die das Maschinen-Ergebnis beschrieben wird.

Die Verifikation ist selbst eine dokumentierte Expert-in-the-Loop-Arbeitsepisode und damit zugleich Material für die qualitative Ebene. Der Gold Standard ist kein Wirksamkeitsmaß des Workflows; er beschreibt die Qualität eines Artefakts gegen eine gesicherte Referenz.

## Korrektur-Protokoll als Dokumentationsgrundlage

Weil jede Accept-, Correct- und Add-Aktion mit Feld, Provenienz, Aktion und Eintragstyp geloggt wird, hinterlässt die Kuration als Nebenprodukt ein Protokoll der Korrektur-Episoden. Das Protokoll hält fest, was wann woran korrigiert wurde, mit welcher Ausgangs-Provenienz und mit welchem Ausgangs- und Zielwert. Es ist Dokumentationsgrundlage für die qualitative Auswertung, kein Messinstrument. Systematische Korrekturmuster sind Werkstattbefunde: korrigiert das Fachpersonal wiederholt dasselbe Feld auf demselben Eintragstyp, ist das ein Signal an den Developer-Loop. Aus dem Protokoll werden keine Wirksamkeits-Kennzahlen des Workflows abgeleitet, kein Score je Iteration und keine Interaktions-Ratio als Erfolgsbeleg. Das Protokoll-Format liegt in [[data#correction-protocol]].

## Arbeitspakete

Geordnet nach Abhängigkeit. Die Reihenfolge ist eine Empfehlung der Lane, kein Operator-Beschluss; die eingebetteten Gate-Fragen markieren, wo eine fachliche Entscheidung vor der Umsetzung nötig ist.

1. **Multi-Edition-Zielmodell, Segmentierung, Verifikation.** Die dominante systematische Feld-Fehlerklasse ist ein Ebenenfehler, kein Extraktionsfehler. Eine Wiki-Seite beschreibt ein Werk, die `'''[Jahr]:'''`-Blöcke beschreiben Ausgaben, der flache Datensatz vermischt beide Ebenen, und die flache Extraktion zieht jedes Feld aus einem beliebigen Block; Regex ist am Limit, siehe [[pipeline#known-limitations--multi-edition-pages]]. Das Arbeitspaket ist deshalb nicht nur Dekomposition, sondern drei zusammenhängende Teile: das Werk/Ausgabe-Zielmodell (`schema:CreativeWork` mit `workExample`, Ausgabe als `schema:Book` mit `exampleOfWork`, stabile quellableitbare Ausgaben-IDs als Vorbedingung), die LLM-gestützte Edition-Block-Segmentierung einer als mehrfach identifizierten Seite in Ausgaben-Knoten, und die Verifikation dieser Knoten (Web-Annotation-Evidenz je Ausgabe, PROV-Provenienz der Segmentierung, SHACL-Vertrag des gültigen Ausgaben-Knotens). Zielmodell, ID-Schema, Provenienz- und Prüfschichten und das Vorgehen mit Stichproben-Gate stehen ausgearbeitet in [[#entscheidungsgrundlage-gate-1-werkausgabe-modell]]. Zuerst, weil viele fehlende Publisher- und Location-Werte von diesen Seiten stammen und weil die Handkorrektur je Feld erst nach der Ebenentrennung eindeutig wird.

2. **Redirect-Auflösung.** Ein Teil der Redirects lässt sich nicht auflösen, weil der Target-Title nicht exakt auf einen bestehenden Eintrag passt, siehe [[pipeline#redirects-as-map-instead-of-resolved-entries]]. Arbeitspaket: die nicht aufgelösten Redirects im Werkzeug zur Editor-Prüfung vorlegen, aufgelöste eintragen, verbleibende mit Begründung als unauflösbar markieren.

3. **Kategorie-Seiten-Auswertung.** Die extrahierten MediaWiki-Kategorie-Seiten sind bisher ungenutzt. Potenzial: reichere Metadaten für Kategorisierung und thematische Cluster sowie strukturelle Hinweise für die Multi-Edition-Dekomposition. Auswertung als eigener Pipeline-Schritt, dessen Ergebnis in die Anreicherung fließt.

4. **Reconciliation.** Die Verknüpfung der offenen Einträge mit dem SZD-Werkindex und externen Normdaten (Wikidata, GND, VIAF, GeoNames) als zweiter Expert-in-the-Loop-Schritt, siehe [[data#wikidata-reconciliation]] und den Forschungsplan im Vault. Kandidaten-Extraktion und Confidence-Ranking werden so aufbereitet, dass der Editor Verknüpfungsvorschläge validieren kann, mit eigener protokollierter Verifikations-Episode. Per Operator-Entscheid vom 2026-07-18 (Gate 2) gehört die Verknüpfungs-Validierung voll in den produktionsreifen Auslieferungsstand; sie setzt die Ausgaben-Ebene aus Arbeitspaket 1 voraus.

5. **Wiki-Druck-Merge mit Feld-Provenienz.** Die Bibliographie liegt in zwei Fassungen vor, dem extrahierten Wiki-Korpus und einer gescannten Druckversion. Welche Information nur im Wiki, nur im Druck oder in beiden steht, ist nicht vorab bekannt und kann unterschiedlichen Redaktionsstand tragen. Arbeitspaket: Druck-Scans segmentieren, per OCR/HTR auf Einträge mappen, gegen die Wiki-Einträge alignieren, den Diff pro Feld als Provenienz-Datenstruktur ablegen (`Wiki` / `Druck` / `beide`) und die Reconstruction-Sicht im Frontend um diese drei Zustände samt Faksimile der Druckseite erweitern. Die Druck-PDFs liegen im SZD-Repository, siehe den Forschungsplan im Vault (Phase B0).

6. **Deployment mit Zitierbarkeit.** Live-Deployment verifizieren (Routen, Suche, Daten laden), Zenodo-Deposit für einen DOI erwägen, `CITATION.cff` pflegen, den Link von Stefan Zweig Digital zur Klawiter-Bibliographie setzen (Abstimmung mit dem Projektteam). Zitierbarkeit heißt, dass die gerettete und kuratierte Ressource stabil adressierbar und als Datenpublikation referenzierbar ist.

## Gates

Diese fachlichen Entscheidungen sind vor der jeweiligen Umsetzung nötig. Sie liegen in einer verdeckten Reihenfolge: der Multi-Edition-Entscheid (Gate 1) ist dem Reconciliation-Tiefe-Entscheid (Gate 2) vorgelagert (die Reconciliation setzt die Ausgaben-Ebene voraus), und der Merge-Scope (Gate 3) profitiert vom selben Modell (er benutzt dessen Provenienz-Schema mit). Die Entscheidungsgrundlage für Gate 1 steht in [[#entscheidungsgrundlage-gate-1-werkausgabe-modell]].

**Stand 2026-07-18: Operator-Entscheide gefallen, Details am Sektionsende.**

1. **Multi-Edition-Behandlung im Editor.** Die als mehrfach identifizierten Seiten im Werkzeug aktiv dekomponieren und kuratieren, oder markieren und zurückstellen? Diese Frage entscheidet, ob Arbeitspaket 1 eine Pipeline- oder eine Editor-Aufgabe wird. Die Modelloptionen, das ID-Schema als Vorbedingung und das Stichproben-Vorgehen für die Entscheidung stehen in [[#entscheidungsgrundlage-gate-1-werkausgabe-modell]].

2. **Reconciliation-Tiefe für die Produktionsreife.** Gehört die Normdaten-Reconciliation (Arbeitspaket 4) in den produktionsreifen Auslieferungsstand des Werkzeugs, oder bleibt sie als nachgelagerte Forschungsaufgabe außerhalb der Produktionsreife? Das entscheidet über den Umfang der Editier-Oberfläche.

3. **Wiki-Druck-Merge im Scope.** Ist der Merge mit der Druckversion (Arbeitspaket 5) Teil der ersten Produktionsreife, oder eine spätere Ausbaustufe? Er bringt eine OCR/HTR-Kette und eine zweite Provenienz-Achse ins Werkzeug und ist der größte Einzelaufwand unter den Paketen.

4. **Modellweg im Auslieferungsstand.** Increment 4 (lebender lokaler Write-Back) und der lokale Modellweg neben dem Cloud-Modell sind angelegt, aber nicht gebaut. Sind beide Teil der Produktionsreife, oder reicht für die Auslieferung der Cloud-Weg mit dem Patch-Datei-Export als portabler Fallback?

### Operator-Entscheide (2026-07-18)

1. **Gate 1, dekomponieren.** Werk/Ausgabe-Trennung nach dem Zielmodell dieser Sektion. Das Stichproben-Gate ist ausgeführt, `pipeline/segment_editions.py` zerlegt die drei prominenten Seiten (Ungeduld des Herzens, Schachnovelle/Volume, Die Welt von Gestern) deterministisch in Ausgaben-Knoten mit stabilen IDs und Offset-Evidenz; Blockabgrenzung gegen die Handzerlegung vollständig korrekt, Befunde und Restfehler der Kopfzeilen-Reinigung in `data/output/edition-samples/REVIEW.md`. Vor dem Vollauf steht die Sichtung durch die Editorin samt der Tiefenentscheidungen (Auflagen-Unterzeilen, Sammelband-Vorkommen über `schema:isPartOf`, dort auch der Befund, dass VIST-Seiten Vorkommens-Listen und keine Ausgaben-Seiten sind).
2. **Gate 2, Reconciliation voll in die Produktionsreife.** Arbeitspaket 4 wird vom Vorbereitungs- zum vollen Umsetzungspaket; die Verknüpfungs-Validierung wird vollwertiger Teil der Editier-Oberfläche. Sauber wird sie erst auf der Ausgaben-Ebene aus Gate 1, daran bleibt die Reihenfolge gebunden.
3. **Gate 3, spätere Ausbaustufe.** Der Wiki-Druck-Merge (Arbeitspaket 5) bleibt außerhalb der ersten Produktionsreife; das Provenienz-Schema des Zielmodells hält ihm den Platz als dritte Evidenzquelle frei.
4. **Gate 4, Patch-Export als Auslieferungsstand.** Der Export-Kontrakt (Patch-v2-Datei, `apply_patches.py`) bleibt der kanonische Weg, weil er ohne laufende Infrastruktur auskommt und jede Korrektur als sichtbares, versionierbares Artefakt trägt. Increment 4 folgt später als Komfortschicht, deren lokaler Endpunkt dieselben Patch-v2-Dateien nach `data/corrections/` schreibt statt sie als Download zu erzeugen.

Folgen für die Schichten: die PROV-Provenienz aus dem Zielmodell gilt für das JSON-LD-Dataset, nicht nur für die Frontend-Kurzform (`klawiter.jsonld` trägt bisher keine Feld-Provenienz); das `klawiter:`-Vokabular liegt seit demselben Datum maschinenlesbar vor (`docs/vocab/klawiter.ttl`), worauf die SHACL-Shapes aufsetzen können. Vor der Prägung des `llmprov`-Profils steht die Nachbarschaftsprüfung (W3C ML Schema u. a.) als eigener Arbeitsschritt.

## EIL-Editing-Increments

Der Bau der Editierschicht folgt fünf Inkrementen; die dauerhafte UI-Spezifikation steht in [[frontend#eil-curation-interface]].

1. **Review-Status + Action-Typing + Session-Durability** (gebaut, Session 19): Drei-Status-Review je Eintrag, jede Interaktion getypt Accept/Correct/Add mit v2-Edit-History-Record, Persistenz in `localStorage`, Save exportiert ein `patchVersion: 2`-Dokument, das `apply_patches.py` liest. Gepinnt durch `tests/test_patch_contract.py`.
2. **Uncertainty-Surface** (gebaut, Session 21): Provenienz-Klassen, verify.py-Flags und Census-Anomalie gebündelt zu Prüfhinweisen je Eintrag (`build_triage.py` → `triage.json` → Hint-Liste, Card-Chip, Feld-Marker, Prüfbedarf-Sortierung). Gepinnt durch `tests/test_triage.py` und `tests/evidence_triage.test.js`. Offener Kalibrierungs-Input ist die stratifizierte Feld-Stichprobe, siehe [[#offener-m38-rest-stratifizierte-feld-stichprobe]].
3. **Editing-Scope** (gebaut für die getrackten Felder, Session 21): Quell-Evidenz neben jedem der vier provenienz-getrackten Felder, feldgenau wo ein Ausschnitt ableitbar ist, sonst der ganze Quelltext einklappbar. Das Editieren über die vier Felder hinaus (Titel vor allem, siehe [[testing#implications-for-the-editing-tool]]) bleibt offen und hängt an der Multi-Edition-Gate-Frage.
4. **Write-Back + Apply-Step** (offen): `apply_patches.py` (Dataset-Overlay, `editor`-Provenienz, Edit-History, idempotente Wiederanwendung aus dem git-getrackten Store) ist implementiert und unit-getestet; offen ist der lebende lokale Endpunkt, der die Korrekturen ohne manuellen Datei-Schritt schreibt. Hängt an Gate 4.
5. **Protocol-Read-out** (offen): das Korrektur-Protokoll (Episoden mit Feld, Aktion, Provenienz) direkt aus der akkumulierten Edit-History ableiten, als Dokumentationsgrundlage für die qualitative Auswertung.

### Offener M3.8-Rest: stratifizierte Feld-Stichprobe

Die Feld-Fidelity-Prüfung in [[testing#field-level-fidelity-findings]] ist ein gezielter, kein erschöpfender Durchgang: sie bestätigt die Fehlerklassen gegen benannte Beispieleinträge und vermisst die Weimar-Klasse vollständig gegen ein committetes Artefakt. Was fehlt, ist eine Feld-Fehlerrate über eine stratifizierte Stichprobe. Diese Messung ist der Kalibrierungs-Input, den das Triage-Signal braucht, damit die Rangordnung der Prüfhinweise gegen verifizierte Fälle geeicht ist, bevor sie Prüfarbeit erzeugt. Sie ist der offene Rest des Arbeitspakets M3.8 und Voraussetzung für die Precision des Triage-Signals aus [[frontend#the-uncertainty-surface]].

## Entscheidungsgrundlage Gate 1: Werk/Ausgabe-Modell

Entscheidungsgrundlage für die Werk/Ausgabe-Modellierung der Multi-Edition-Seiten und die Provenienz-, Evidenz- und Prüfschichten, die diese Modellierung tragen. Ergebnis der Modellierungsrunde vom 2026-07-18. Diese Sektion legt die Modelloptionen und ihre Fundierung offen, damit die Gate-1-Entscheidung darauf aufsetzen kann. Sie schließt an den Vokabular-Blend in [[data#data-model]] an und erweitert ihn um eine Ebene, ohne den JSON-LD-Stack zu wechseln. Die Multi-Edition-Grenze der Pipeline, aus der sie hervorgeht, steht in [[pipeline#known-limitations--multi-edition-pages]].

### Befund: ein Ebenenfehler, kein Extraktionsfehler

Die Multi-Edition-Seite ist kein Extraktionsfehler, den bessere Regex oder ein schärferer LLM-Prompt schließen. Sie ist ein Ebenenfehler im Datenmodell. Eine Wiki-Seite beschreibt ein Werk, die `'''[Jahr]:'''`-Blöcke auf derselben Seite beschreiben einzelne Ausgaben dieses Werks. Der heutige flache Datensatz hält beide Ebenen in einem Objekt und vermischt sie. First-match-wins zieht Verlag, Jahr und Ort aus einem beliebigen Block, weshalb diese Felder auf den betroffenen Seiten systematisch unzuverlässig sind, Details und Feldwirkung in [[pipeline#known-limitations--multi-edition-pages]].

Handkorrektur heilt das nicht. Für einen flachen Datensatz, der mehrere Ausgaben zusammenfasst, gibt es keinen einen richtigen Verlag, den die Editorin eintragen könnte; jede Wahl ist für die übrigen Ausgaben falsch. Die Editier-Oberfläche macht die Ambiguität am Feld bereits sichtbar (Fundstellenzähler in Increment 3, [[frontend#source-evidence-per-field]]), aber sichtbar machen ist nicht auflösen, solange das Zielobjekt flach bleibt. Einträge, deren Titel selbst eine `'''[Jahr]:'''`-Kopfzeile ist (die Bracket-Titel aus [[data#known-problems]]), sind Symptome derselben Ursache, ein Ausgaben-Header, der mangels Werk-Ebene zum Titel des ganzen Datensatzes wird.

Die Konsequenz für die Arbeitspakete: die Multi-Edition-Behandlung ist Modellarbeit vor Extraktionsarbeit. Erst wenn Werk und Ausgabe getrennte Objekte sind, wird die Segmentierung überhaupt eine wohldefinierte Aufgabe, und erst dann wird die Handkorrektur je Ausgabe eindeutig. Von den Wiki-Seiten sind rund 427 als mehrfach identifiziert (6,8 %, Stand 2026-07-18).

### Zielmodell: Werk/Ausgabe-Trennung

Das Zielmodell trennt Werk und Ausgabe in zwei Objektebenen und bleibt dabei im vorhandenen JSON-LD-Stack, kein Ontologiewechsel.

- Das Werk ist ein `schema:CreativeWork` und verweist über `schema:workExample` auf seine Ausgaben.
- Die Ausgabe ist ein `schema:Book` und verweist über `schema:exampleOfWork` zurück auf das Werk.
- Verlag, Ort, Jahr, Seitenzahl, Übersetzer wandern auf die Ausgabe, wo sie hingehören; Titel, Autor, Werk-Identität und die werkübergreifenden Querverweise bleiben am Werk.

Theoretisch ist das die Work/Manifestation-Unterscheidung aus FRBR/LRM und die Work/Instance-Unterscheidung aus BIBFRAME, ausgedrückt in schema.org-Vokabular. Der Vokabular-Blend lehnt BIBFRAME als Serialisierung ab (kein offizieller JSON-LD-Kontext), nicht die konzeptuelle Trennung; die Trennung selbst ist Bibliotheksstandard und wird hier über `workExample`/`exampleOfWork` realisiert, für die schema.org einen JSON-LD-Kontext liefert.

Ein-Ausgaben-Seiten bleiben trivial. Werk und einzige Ausgabe können zu einem Objekt zusammenfallen oder trivial getrennt werden; für die große Mehrheit der Seiten ändert sich nichts an der sichtbaren Struktur, nur die Multi-Edition-Seiten gewinnen die zweite Ebene.

#### Beispiel: Seite 4916 (Schachnovelle)

Der heutige flache Datensatz zieht Verlag und Ort aus der Erstausgabe und stellt sie als die Werte des ganzen Datensatzes dar:

```json
{
  "@id": "klawiter:entry/4916",
  "@type": "klawiter:FictionEntry",
  "title": "Schachnovelle",
  "year": 1942,
  "publisher": "Pigmalión",
  "location": "Buénos Aires",
  "sourcePageId": 4916
}
```

`publisher` und `locationCreated` gehören zur Erstausgabe 1942 (Pigmalión, Buenos Aires), nicht zum Werk; jede spätere Ausgabe der Schachnovelle hat einen anderen Verlag und Ort, die der flache Datensatz nicht trägt. Im Zielmodell trägt das Werk die Identität und verweist auf die Ausgaben:

```json
{
  "@id": "klawiter:work/4916",
  "@type": "schema:CreativeWork",
  "name": "Schachnovelle",
  "author": { "@type": "schema:Person", "name": "Stefan Zweig",
              "sameAs": "https://www.wikidata.org/entity/Q78491" },
  "workExample": [
    { "@id": "klawiter:edition/4916-1942-a" },
    { "@id": "klawiter:edition/4916-1943-a" }
  ]
}
```

```json
{
  "@id": "klawiter:edition/4916-1942-a",
  "@type": "schema:Book",
  "exampleOfWork": { "@id": "klawiter:work/4916" },
  "datePublished": "1942",
  "publisher": "Pigmalión",
  "locationCreated": "Buénos Aires"
}
```

Der Verlag steht jetzt an der Ausgabe, an die er gehört, und die übrigen Ausgaben tragen ihre eigenen Werte statt der ersterhaltenen.

### ID-Schema als Vorbedingung

Jede Segmentierung braucht vorab ein stabiles, quellableitbares ID-Schema für die Ausgaben-Knoten, sonst zerfällt der Zusammenhang zwischen einer Neusegmentierung und allem, was auf die alten IDs zeigt. Vorschlag:

```
klawiter:edition/{pageId}-{jahr}-{laufbuchstabe}
```

`pageId` verankert die Ausgabe an der Quellseite, `jahr` an ihrem Ausgaben-Header, der `laufbuchstabe` unterscheidet mehrere Ausgaben desselben Jahres auf derselben Seite. Die ID ist damit aus der Quelle ableitbar und nicht aus einer laufenden Zählung, die sich bei jedem Neulauf verschieben würde.

Stabilitätsregel: eine erneute Segmentierung darf bestehende IDs nicht verwürfeln. An den Ausgaben-IDs hängen die Editor-Patches (`apply_patches.py` adressiert das korrigierte Feld über die Entry-ID), das Korrektur-Protokoll und die Zitierbarkeit einzelner Ausgaben. Ändert ein Neulauf die IDs, verlieren Patches ihren Anker und das Protokoll seine Referenz. Das Schema muss deshalb deterministisch aus dem Quellblock folgen, damit dieselbe Ausgabe über Läufe hinweg dieselbe ID trägt.

### Evidenz je Ausgabe

Jeder Ausgaben-Knoten braucht die Fundstelle seines Quellblocks, damit die Zuordnung Block-zu-Ausgabe nachprüfbar ist. Statt einer Ad-hoc-Struktur die W3C Web Annotation:

```json
{
  "@type": "oa:Annotation",
  "oa:hasTarget": {
    "oa:hasSource": { "@id": "klawiter:sourceText/4916" },
    "oa:hasSelector": {
      "@type": "oa:TextPositionSelector",
      "oa:start": 512,
      "oa:end": 691
    }
  },
  "oa:hasBody": { "@id": "klawiter:edition/4916-1942-a" }
}
```

Das `oa:TextPositionSelector` benennt den Zeichenbereich im Quelltext (`sourceTextId`), aus dem die Ausgabe segmentiert wurde. Das schließt an die vorhandene Quell-Evidenz-Mechanik aus Increment 3 an ([[frontend#source-evidence-per-field]]), die schon heute den feldtragenden Ausschnitt im Quelltext lokalisiert; die Web Annotation hebt denselben Befund von der Feld- auf die Ausgaben-Ebene und macht ihn als standardkonformes Objekt zitierbar.

### Provenienz-Schicht: PROV-O als Rückgrat

Die volle Provenienz jeder segmentierten Ausgabe wird mit PROV-O ausgedrückt. Die Rollen:

- `prov:Entity` für die Artefakte (Quellblock, Ausgaben-Knoten, Segmentierungs-Report).
- `prov:Activity` für die Pipeline-Schritte (die Segmentierung, die Extraktion, die Verifikation).
- `prov:SoftwareAgent` für das Skript, gepinnt auf seinen Commit-Hash, und für das LLM, mit Modellname und Version.
- `prov:Person` für die Editorin, als Rolle, nicht als Name (Datenschutz-Konvention aus [[about#data-integrity-principle]]).
- Der Prompt als `prov:Plan`, angebunden über `prov:qualifiedAssociation`/`prov:hadPlan` und ebenfalls auf einen Commit gepinnt, damit nachvollziehbar bleibt, welcher Prompt welche Segmentierung erzeugt hat.

Das bestehende `_provenance`-Feld (`regex`/`llm`/`missing`/`editor`, [[data#provenance-metadata-_provenance]]) bleibt unverändert als abgeleitete Kurzform für das Frontend. Es ist die eine Zeile, die die Oberfläche je Feld braucht, um dem Fachpersonal die Sicherheit der Extraktion anzuzeigen. Der volle PROV-Graph liegt nicht im Frontend-JSON, sondern als Sidecar oder Named Graph daneben, damit das ausgelieferte `klawiter.json` schlank bleibt. Die Kurzform ist eine Projektion des Graphen, keine zweite Wahrheit; wer die Kette braucht, liest den Graphen, wer nur das Badge braucht, liest das Feld.

### Prüfschicht: SHACL, EARL, DQV

Das Zielmodell braucht einen ausführbaren Vertrag, der sagt, was ein gültiger Ausgaben-Knoten ist. Diesen Vertrag tragen SHACL-Shapes: welche Felder eine Ausgabe haben muss, welche Typen und Kardinalitäten gelten, wann ein `exampleOfWork` auf ein existierendes Werk zeigen muss. Die Shapes sind der maschinenprüfbare Ausdruck des in dieser Sektion beschriebenen Modells.

Die Prüfergebnisse werden nicht als formloser Report abgelegt, sondern als EARL-Assertions. `earl:automatic` markiert eine deterministische Prüfung, `earl:manual` eine menschliche Verifikation; die Unterscheidung hält auseinander, was die Maschine geprüft hat und was das Fachpersonal bestätigt hat, dieselbe Grenze, die der Gold Standard in [[#gold-standard-als-messbarer-baustein]] zieht. Aggregiert lassen sich Prüfergebnisse zusätzlich als DQV-Qualitätsmaße ausdrücken, wo ein zusammengefasstes Maß über viele Knoten gebraucht wird. Der SHACL-Report selbst wird per PROV an den Lauf gehängt, der ihn erzeugt hat, damit auch die Prüfung ihre eigene Provenienz trägt.

### Profil-Skizze: llmprov

Statt PROV neu zu bauen, ein schmales Erweiterungsprofil `llmprov`, das nur prägt, was PROV nicht schon sagt, und alles andere von PROV erbt. Die Subklassen:

- `llmprov:ModelRun` (Subklasse von `prov:Activity`) für einen LLM-Lauf.
- `llmprov:DeterministicRun` (Subklasse von `prov:Activity`) für einen regelbasierten, wiederholbaren Lauf.
- `llmprov:Prompt` (Subklasse von `prov:Plan`) für den Prompt, der einen Lauf steuert.
- `llmprov:Model` (Subklasse von `prov:SoftwareAgent`) mit Anbieter, Modellname und Version.
- `llmprov:Source` (Subklasse von `prov:Entity`), verknüpft mit der Web-Annotation-Fundstelle, für den Quellblock einer Ausgabe.
- `llmprov:VerificationEpisode` (Subklasse von `prov:Activity`) für eine Prüfepisode, deren Modus über EARL (`earl:automatic`/`earl:manual`) festgehalten wird.

Designregeln für das Profil:

- Nur prägen, was PROV nicht sagt. Jede Subklasse muss einen Unterschied tragen, den `prov:Activity`/`prov:Entity`/`prov:Agent` nicht ausdrücken.
- Die Nachbarschaft prüfen, bevor geprägt wird, insbesondere das W3C ML Schema und verwandte Vokabulare für Modell- und Laufbeschreibung; ein vorhandenes Term wird wiederverwendet statt neu erfunden.
- Klein halten. Das Profil ist eine Handvoll Subklassen, kein Vokabular.
- Als publizierbares Deliverable anlegen (Turtle plus SHACL-Shapes plus Dokumentation, unter einer versionierten Namespace-URI), damit es in den anderen DIA-XAI-Werkzeugen wiederverwendbar ist. Der geteilte Kurationskern der Werkzeugfamilie legt genau diese Wiederverwendung nahe.

Ein kompaktes Turtle-Beispiel, ein Ausgaben-Knoten mit seiner Erzeugung, seinem Agenten, seinem Prompt und einer Verifikations-Episode:

```turtle
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix earl:    <http://www.w3.org/ns/earl#> .
@prefix llmprov: <https://chpollin.github.io/klawiter-rescue/llmprov/> .
@prefix kl:      <https://chpollin.github.io/klawiter-rescue/vocab/> .

kl:edition/4916-1942-a
    prov:wasGeneratedBy   kl:run/segment-4916 .

kl:run/segment-4916
    a                     llmprov:ModelRun ;
    prov:used             kl:sourceText/4916 ;
    prov:wasAssociatedWith kl:agent/gemini ;
    prov:qualifiedAssociation [
        a                 prov:Association ;
        prov:agent        kl:agent/gemini ;
        prov:hadPlan      kl:prompt/segment-v1
    ] .

kl:agent/gemini
    a                     llmprov:Model ;
    llmprov:provider      "Google" ;
    llmprov:modelName     "gemini-3.1-flash-lite-preview" ;
    llmprov:modelVersion  "2026-06" .

kl:prompt/segment-v1
    a                     llmprov:Prompt ;
    prov:atLocation       "pipeline/prompts/segment.md@<commit>" .

kl:verify/4916-1942-a
    a                     llmprov:VerificationEpisode ;
    prov:used             kl:edition/4916-1942-a ;
    earl:mode             earl:manual ;
    earl:result           [ earl:outcome earl:passed ] .
```

### Tiefenentscheidungen (zu benennen, nicht zu entscheiden)

Zwei Modellierungsfragen liegen unterhalb der Werk/Ausgabe-Trennung und sind der Editorin vorzulegen, sobald die Segmentierung steht:

- Auflagen-Unterzeilen. Ein Ausgaben-Block trägt oft Auflagen-Angaben (`*1st edition ... copies`). Diese als eigene Knoten mit `schema:bookEdition` modellieren, oder zunächst als strukturierte `schema:description` an der Ausgabe halten und die Feingranularität später ziehen.
- Sammelband-Vorkommen. Erscheint ein Werk innerhalb eines Sammelbands, ist das über `schema:isPartOf` von der Ausgabe auf den Sammelband auszudrücken; offen ist, wie weit die Sammelband-Knoten selbst ausmodelliert werden.

### Vorgehen

- Stichproben-Gate vor Vollauf. Die Segmentierung zuerst an drei prominenten Seiten erproben (Schachnovelle, Ungeduld des Herzens, Die Welt von Gestern), mit Sichtung durch die Editorin, bevor ein Vollauf über alle mehrfach identifizierten Seiten läuft.
- Messgröße. Der Anteil korrekt abgegrenzter Blöcke gegen eine Handzerlegung derselben Seiten; die Handzerlegung ist die Referenz, gegen die die maschinelle Segmentierung beschrieben wird, analog zum Gold Standard je Feld.
- Triage. Nur Seiten segmentieren, die als mehrfach identifiziert markiert sind; Ein-Ausgaben-Seiten bleiben unangetastet.
- Frontend-Konsequenz. Die Werk-Karte trägt eine aufklappbare Ausgabenliste; die Detailsicht zeigt das Werk mit seinen Ausgaben statt eines flachen Datensatzes.
- Gold Standard je Ebene getrennt. Werk-Felder (Titel, Autor, Werk-Identität) und Ausgaben-Felder (Verlag, Ort, Jahr, Seitenzahl) werden getrennt gezählt, weil die Extraktionsqualität auf den beiden Ebenen verschieden ist und eine gemischte Zählung sie verwischt.

### Einordnung

Erst die Ausgaben-Ebene macht die Reconciliation sinnvoll. Wikidata und GND trennen Werk und Ausgabe genauso; ein flacher Datensatz, der beide vermischt, lässt sich gegen diese Normdaten nicht sauber abgleichen, weil unklar ist, ob ein Kandidat das Werk oder eine Ausgabe meint. Auf der Ausgaben-Ebene werden zudem Verlagsgeschichte, Lizenzausgaben und Übersetzungswege abfragbar, die der flache Datensatz kollabiert.

Der Wiki-Druck-Merge (Arbeitspaket 5) profitiert vom selben Modell. Wo Wiki und Druck sich unterscheiden, ist das eine dritte Evidenzquelle je Ausgabe, die im selben Provenienz-Schema (`Wiki`/`Druck`/`beide`) neben der Segmentierungs-Provenienz liegt, statt einer eigenen, konkurrierenden Struktur.

## Related

- [[about#dia-xai-connection]] — Evaluationsrahmung: Gold Standard messbar, Protokoll qualitativ
- [[frontend#eil-curation-interface]] — dauerhafte Spezifikation der Editierschicht
- [[data#correction-protocol]] — Format des Korrektur-Protokolls
- [[testing#field-level-fidelity-findings]] — Feld-Fehlerklassen, auf denen die Arbeitspakete aufsetzen
- [[pipeline#known-limitations--multi-edition-pages]] — Multi-Edition-Grenze der Pipeline
