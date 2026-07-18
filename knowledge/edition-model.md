---
title: Edition Model
aliases: [edition-model, Werk-Ausgabe-Modell, work-edition split, multi-edition modeling, PROV, SHACL, llmprov]
tags: [ontology, data, eil, dia-xai, plan]
created: 2026-07-18
updated: 2026-07-18
---

# Edition Model

Entscheidungsgrundlage für die Werk/Ausgabe-Modellierung der Multi-Edition-Seiten und die Provenienz-, Evidenz- und Prüfschichten, die diese Modellierung tragen. Ergebnis der Modellierungsrunde mit dem Operator vom 2026-07-18. Dieses Dokument entscheidet keine der offenen Operator-Gate-Fragen aus [[production-readiness#braucht-den-operator]]; es legt die Modelloptionen und ihre Fundierung so offen, dass die fachliche Entscheidung darauf aufsetzen kann. Es schließt an das bestehende Vokabular-Dokument [[ontology]] an und erweitert es um eine Ebene, ohne den JSON-LD-Stack zu wechseln. Die Multi-Edition-Grenze der Pipeline, aus der es hervorgeht, steht in [[pipeline#known-limitations--multi-edition-pages]].

## Befund: ein Ebenenfehler, kein Extraktionsfehler

Die Multi-Edition-Seite ist kein Extraktionsfehler, den bessere Regex oder ein schärferer LLM-Prompt schließen. Sie ist ein Ebenenfehler im Datenmodell. Eine Wiki-Seite beschreibt ein Werk, die `'''[Jahr]:'''`-Blöcke auf derselben Seite beschreiben einzelne Ausgaben dieses Werks. Der heutige flache Datensatz hält beide Ebenen in einem Objekt und vermischt sie. First-match-wins zieht Verlag, Jahr und Ort aus einem beliebigen Block, weshalb diese Felder auf den betroffenen Seiten systematisch unzuverlässig sind, Details und Feldwirkung in [[pipeline#known-limitations--multi-edition-pages]].

Handkorrektur heilt das nicht. Für einen flachen Datensatz, der mehrere Ausgaben zusammenfasst, gibt es keinen einen richtigen Verlag, den die Editorin eintragen könnte; jede Wahl ist für die übrigen Ausgaben falsch. Die Editier-Oberfläche macht die Ambiguität am Feld bereits sichtbar (Fundstellenzähler in Increment 3, [[eil-editing#current-klawiter-state]]), aber sichtbar machen ist nicht auflösen, solange das Zielobjekt flach bleibt. Einträge, deren Titel selbst eine `'''[Jahr]:'''`-Kopfzeile ist (die Bracket-Titel aus [[data#known-problems]]), sind Symptome derselben Ursache, ein Ausgaben-Header, der mangels Werk-Ebene zum Titel des ganzen Datensatzes wird.

Die Konsequenz für die Arbeitspakete: die Multi-Edition-Behandlung ist Modellarbeit vor Extraktionsarbeit. Erst wenn Werk und Ausgabe getrennte Objekte sind, wird die Segmentierung überhaupt eine wohldefinierte Aufgabe, und erst dann wird die Handkorrektur je Ausgabe eindeutig.

## Zielmodell: Werk/Ausgabe-Trennung

Das Zielmodell trennt Werk und Ausgabe in zwei Objektebenen und bleibt dabei im vorhandenen JSON-LD-Stack aus [[ontology]], kein Ontologiewechsel.

- Das Werk ist ein `schema:CreativeWork` und verweist über `schema:workExample` auf seine Ausgaben.
- Die Ausgabe ist ein `schema:Book` und verweist über `schema:exampleOfWork` zurück auf das Werk.
- Verlag, Ort, Jahr, Seitenzahl, Übersetzer wandern auf die Ausgabe, wo sie hingehören; Titel, Autor, Werk-Identität und die werkübergreifenden Querverweise bleiben am Werk.

Theoretisch ist das die Work/Manifestation-Unterscheidung aus FRBR/LRM und die Work/Instance-Unterscheidung aus BIBFRAME, ausgedrückt in schema.org-Vokabular. Der Design-Rationale in [[ontology#design-rationale]] lehnt BIBFRAME als Serialisierung ab (kein offizieller JSON-LD-Kontext), nicht die konzeptuelle Trennung; die Trennung selbst ist Bibliotheksstandard und wird hier über `workExample`/`exampleOfWork` realisiert, für die schema.org einen JSON-LD-Kontext liefert.

Ein-Ausgaben-Seiten bleiben trivial. Werk und einzige Ausgabe können zu einem Objekt zusammenfallen oder trivial getrennt werden; für die große Mehrheit der Seiten ändert sich nichts an der sichtbaren Struktur, nur die Multi-Edition-Seiten gewinnen die zweite Ebene.

### Beispiel: Seite 4916 (Schachnovelle)

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

## ID-Schema als Vorbedingung

Jede Segmentierung braucht vorab ein stabiles, quellableitbares ID-Schema für die Ausgaben-Knoten, sonst zerfällt der Zusammenhang zwischen einer Neusegmentierung und allem, was auf die alten IDs zeigt. Vorschlag:

```
klawiter:edition/{pageId}-{jahr}-{laufbuchstabe}
```

`pageId` verankert die Ausgabe an der Quellseite, `jahr` an ihrem Ausgaben-Header, der `laufbuchstabe` unterscheidet mehrere Ausgaben desselben Jahres auf derselben Seite. Die ID ist damit aus der Quelle ableitbar und nicht aus einer laufenden Zählung, die sich bei jedem Neulauf verschieben würde.

Stabilitätsregel: eine erneute Segmentierung darf bestehende IDs nicht verwürfeln. An den Ausgaben-IDs hängen die Editor-Patches (`apply_patches.py` adressiert das korrigierte Feld über die Entry-ID, [[eil-editing#persistence-and-how-it-is-saved]]), das Korrektur-Protokoll und die Zitierbarkeit einzelner Ausgaben. Ändert ein Neulauf die IDs, verlieren Patches ihren Anker und das Protokoll seine Referenz. Das Schema muss deshalb deterministisch aus dem Quellblock folgen, damit dieselbe Ausgabe über Läufe hinweg dieselbe ID trägt.

## Evidenz je Ausgabe

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

Das `oa:TextPositionSelector` benennt den Zeichenbereich im Quelltext (`sourceTextId`), aus dem die Ausgabe segmentiert wurde. Das schließt an die vorhandene Quell-Evidenz-Mechanik aus Increment 3 an ([[eil-editing#current-klawiter-state]]), die schon heute den feldtragenden Ausschnitt im Quelltext lokalisiert; die Web Annotation hebt denselben Befund von der Feld- auf die Ausgaben-Ebene und macht ihn als standardkonformes Objekt zitierbar.

## Provenienz-Schicht: PROV-O als Rückgrat

Die volle Provenienz jeder segmentierten Ausgabe wird mit PROV-O ausgedrückt. Die Rollen:

- `prov:Entity` für die Artefakte (Quellblock, Ausgaben-Knoten, Segmentierungs-Report).
- `prov:Activity` für die Pipeline-Schritte (die Segmentierung, die Extraktion, die Verifikation).
- `prov:SoftwareAgent` für das Skript, gepinnt auf seinen Commit-Hash, und für das LLM, mit Modellname und Version.
- `prov:Person` für die Editorin, als Rolle, nicht als Name (Datenschutz-Konvention aus [[about#data-integrity-principle]]).
- Der Prompt als `prov:Plan`, angebunden über `prov:qualifiedAssociation`/`prov:hadPlan` und ebenfalls auf einen Commit gepinnt, damit nachvollziehbar bleibt, welcher Prompt welche Segmentierung erzeugt hat.

Das bestehende `_provenance`-Feld (`regex`/`llm`/`missing`/`editor`, [[data#provenance-metadata-_provenance]]) bleibt unverändert als abgeleitete Kurzform für das Frontend. Es ist die eine Zeile, die die Oberfläche je Feld braucht, um dem Fachpersonal die Sicherheit der Extraktion anzuzeigen. Der volle PROV-Graph liegt nicht im Frontend-JSON, sondern als Sidecar oder Named Graph daneben, damit das ausgelieferte `klawiter.json` schlank bleibt. Die Kurzform ist eine Projektion des Graphen, keine zweite Wahrheit; wer die Kette braucht, liest den Graphen, wer nur das Badge braucht, liest das Feld.

## Prüfschicht: SHACL, EARL, DQV

Das Zielmodell braucht einen ausführbaren Vertrag, der sagt, was ein gültiger Ausgaben-Knoten ist. Diesen Vertrag tragen SHACL-Shapes: welche Felder eine Ausgabe haben muss, welche Typen und Kardinalitäten gelten, wann ein `exampleOfWork` auf ein existierendes Werk zeigen muss. Die Shapes sind der maschinenprüfbare Ausdruck des in diesem Dokument beschriebenen Modells.

Die Prüfergebnisse werden nicht als formloser Report abgelegt, sondern als EARL-Assertions. `earl:automatic` markiert eine deterministische Prüfung, `earl:manual` eine menschliche Verifikation; die Unterscheidung hält auseinander, was die Maschine geprüft hat und was das Fachpersonal bestätigt hat, dieselbe Grenze, die der Gold Standard in [[production-readiness#gold-standard-als-messbarer-baustein]] zieht. Aggregiert lassen sich Prüfergebnisse zusätzlich als DQV-Qualitätsmaße ausdrücken, wo ein zusammengefasstes Maß über viele Knoten gebraucht wird. Der SHACL-Report selbst wird per PROV an den Lauf gehängt, der ihn erzeugt hat, damit auch die Prüfung ihre eigene Provenienz trägt.

## Profil-Skizze: llmprov

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
- Als publizierbares Deliverable anlegen (Turtle plus SHACL-Shapes plus Dokumentation, unter einer versionierten Namespace-URI), damit es in den anderen DIA-XAI-Werkzeugen wiederverwendbar ist. Der geteilte Kurationskern der Werkzeugfamilie ([[eil-editing#shared-curation-spine]]) legt genau diese Wiederverwendung nahe.

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

## Tiefenentscheidungen (zu benennen, nicht zu entscheiden)

Zwei Modellierungsfragen liegen unterhalb der Werk/Ausgabe-Trennung und sind der Editorin vorzulegen, sobald die Segmentierung steht:

- Auflagen-Unterzeilen. Ein Ausgaben-Block trägt oft Auflagen-Angaben (`*1st edition ... copies`). Diese als eigene Knoten mit `schema:bookEdition` modellieren, oder zunächst als strukturierte `schema:description` an der Ausgabe halten und die Feingranularität später ziehen.
- Sammelband-Vorkommen. Erscheint ein Werk innerhalb eines Sammelbands, ist das über `schema:isPartOf` von der Ausgabe auf den Sammelband auszudrücken; offen ist, wie weit die Sammelband-Knoten selbst ausmodelliert werden.

## Vorgehen

- Stichproben-Gate vor Vollauf. Die Segmentierung zuerst an drei prominenten Seiten erproben (Schachnovelle, Ungeduld des Herzens, Die Welt von Gestern), mit Sichtung durch die Editorin, bevor ein Vollauf über alle mehrfach identifizierten Seiten läuft.
- Messgröße. Der Anteil korrekt abgegrenzter Blöcke gegen eine Handzerlegung derselben Seiten; die Handzerlegung ist die Referenz, gegen die die maschinelle Segmentierung beschrieben wird, analog zum Gold Standard je Feld.
- Triage. Nur Seiten segmentieren, die als mehrfach identifiziert markiert sind; Ein-Ausgaben-Seiten bleiben unangetastet.
- Frontend-Konsequenz. Die Werk-Karte trägt eine aufklappbare Ausgabenliste; die Detailsicht zeigt das Werk mit seinen Ausgaben statt eines flachen Datensatzes.
- Gold Standard je Ebene getrennt. Werk-Felder (Titel, Autor, Werk-Identität) und Ausgaben-Felder (Verlag, Ort, Jahr, Seitenzahl) werden getrennt gezählt, weil die Extraktionsqualität auf den beiden Ebenen verschieden ist und eine gemischte Zählung sie verwischt.

## Einordnung

Erst die Ausgaben-Ebene macht die Reconciliation sinnvoll. Wikidata und GND trennen Werk und Ausgabe genauso; ein flacher Datensatz, der beide vermischt, lässt sich gegen diese Normdaten nicht sauber abgleichen, weil unklar ist, ob ein Kandidat das Werk oder eine Ausgabe meint. Auf der Ausgaben-Ebene werden zudem Verlagsgeschichte, Lizenzausgaben und Übersetzungswege abfragbar, die der flache Datensatz kollabiert.

Der Wiki-Druck-Merge (Arbeitspaket 5 in [[production-readiness#arbeitspakete]]) profitiert vom selben Modell. Wo Wiki und Druck sich unterscheiden, ist das eine dritte Evidenzquelle je Ausgabe, die im selben Provenienz-Schema (`Wiki`/`Druck`/`beide`) neben der Segmentierungs-Provenienz liegt, statt einer eigenen, konkurrierenden Struktur.

## Offen für den Operator

Die vier Gate-Fragen aus [[production-readiness#braucht-den-operator]] bleiben offen; dieses Dokument entscheidet keine davon, es ist ihre Entscheidungsgrundlage. Die verdeckte Reihenfolge unter den Fragen: der Multi-Edition-Entscheid (Gate 1) ist dem Reconciliation-Tiefe-Entscheid (Gate 2) vorgelagert, weil die Reconciliation die Ausgaben-Ebene voraussetzt; der Merge-Scope (Gate 3) profitiert vom Modell, weil er dessen Provenienz-Schema mitbenutzt. Wird Gate 1 zugunsten der Segmentierung entschieden, wird Arbeitspaket 1 Modell- und Pipeline-Arbeit nach diesem Dokument; wird es zurückgestellt, bleibt der flache Datensatz mit sichtbar gemachter, aber nicht aufgelöster Ambiguität.

## Related

- [[ontology]] — Vokabular-Blend und JSON-LD-@context, die dieses Modell erweitert
- [[pipeline#known-limitations--multi-edition-pages]] — die Multi-Edition-Grenze der flachen Extraktion, Zahlen und Feldwirkung
- [[production-readiness#arbeitspakete]] — Arbeitspaket 1 (Zielmodell, Segmentierung, Verifikation) und die Gate-Fragen
- [[eil-editing#current-klawiter-state]] — Quell-Evidenz je Feld (Increment 3), an die die Web-Annotation-Evidenz anschließt
- [[eil-editing#shared-curation-spine]] — der geteilte Kurationskern, in dem das llmprov-Profil wiederverwendbar wird
- [[data#provenance-metadata-_provenance]] — das `_provenance`-Kurzformfeld, das als Projektion des PROV-Graphen bleibt
- [[validation]] — die Feldfehler-Klassen, aus denen die Multi-Edition-Klasse hervorsticht
