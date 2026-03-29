# User Stories

User stories for the Klawiter Bibliography frontend. Derived from the target audience (Zweig scholars, librarians, DH researchers) and the data structure (4,751 entries, 15 types, 41 languages, 402 locations).

The original Klawiter bibliography was a MediaWiki. Users are familiar with category-based browsing and expect to navigate by topic, not by statistics.

---

## Personas

**Anna** — Germanistik-Professorin, forscht zu Zweigs Novellistik. Nutzte das Klawiter-Wiki regelmäßig. Will schnell alle Belletristik-Einträge zu einem bestimmten Werk finden und vollständige bibliographische Daten für Zitationen.

**Carlos** — Bibliothekar an einer Romanistik-Fakultät. Sucht spanische Zweig-Übersetzungen für den Bestandsaufbau. Braucht Verlag, Ort, Jahr in exportierbarer Form.

**Mei** — DH-Forscherin, untersucht die globale Rezeption deutschsprachiger Literatur. Interessiert sich für Verteilung nach Sprache, Zeitraum und Geographie. Will die Daten als JSON-LD für eigene Analysen.

---

## Startseite: Orientierung

> **S1**: Als Wiki-gewohnte Nutzerin will ich auf der Startseite sofort sehen, welche **Kategorien** von Einträgen es gibt (Belletristik, Essays, Lyrik, ...), damit ich mich wie im alten Wiki zurechtfinde.

> **S2**: Als Erstbesucherin will ich einen kurzen **Einführungstext** lesen, der erklärt, was die Klawiter-Bibliographie ist und was ich hier finden kann.

> **S3**: Als Nutzerin will ich direkt von der Startseite aus **suchen** können, ohne erst navigieren zu müssen.

**Daten-Check**: 15 entryTypes mit Counts verfügbar. Einführungstext wird redaktionell erstellt. Suche über FlexSearch-Index wie bisher.

**Startseite = Kategorie-Portal**, nicht Dashboard. Die 15 Typen werden als klickbare Kacheln dargestellt, gruppiert nach Zweigs Werkgattungen (Primärwerke) und Sekundärem:

```
WERKE                           REZEPTION
┌──────────┐ ┌──────────┐      ┌──────────────────┐ ┌──────────┐
│Belletrist.│ │  Essays  │      │Sekundärliteratur │ │  Film /  │
│  1.118    │ │   905    │      │     1.406        │ │  Oper 92 │
└──────────┘ └──────────┘      └──────────────────┘ └──────────┘
┌──────────┐ ┌──────────┐      ┌──────────┐ ┌──────────────────┐
│  Lyrik   │ │ Dramatik │      │Symposien │ │Dramat. Lesungen  │
│   275    │ │    43    │      │    39    │ │       18         │
└──────────┘ └──────────┘      └──────────┘ └──────────────────┘
┌──────────┐ ┌──────────┐
│  Briefe  │ │Vor-/Nach-│      EDITIONEN
│   109    │ │worte  36 │      ┌──────────┐ ┌──────────────────┐
└──────────┘ └──────────┘      │Ges. Werke│ │  Übersetzungen   │
┌──────────┐                   │   114    │ │  (von SZ)  56    │
│Hist. Stud.│                  └──────────┘ └──────────────────┘
│   535    │
└──────────┘
```

---

## Stöbern & Suchen: Finden

> **S4**: Als Forscherin will ich alle Einträge eines **Typs** sehen (z.B. "alle Belletristik"), um einen Überblick über Zweigs Prosawerk zu bekommen.

> **S5**: Als Bibliothekar will ich nach **Sprache** filtern (z.B. "Spanisch"), um Übersetzungen in einer bestimmten Sprache zu finden.

> **S6**: Als Nutzerin will ich **mehrere Filter kombinieren** (z.B. Typ + Sprache + Zeitraum), um gezielt zu suchen.

> **S7**: Als Nutzerin will ich die Ergebnisse nach **Jahr, Titel oder Relevanz** sortieren können.

> **S8**: Als Nutzerin will ich sehen, **wie viele Ergebnisse** mein Filter liefert, und aktive Filter als **Chips** sehen und einzeln entfernen können.

**Daten-Check**: Alle Facetten (Typ, Sprache, Zeitraum, Ort) sind als Felder vorhanden. 41 Sprachen, 402 Orte, 5 Zeiträume. Kombinierte Filter funktionieren über Array-Intersection.

---

## Detailansicht: Verstehen

> **S9**: Als Forscherin will ich **alle verfügbaren Metadaten** eines Eintrags in einer strukturierten Übersicht sehen (Titel, Jahr, Verlag, Ort, Sprache, Seitenzahl, Übersetzer).

> **S10**: Als Nutzerin will ich den **vollständigen bibliographischen Eintrag** im Originalformat sehen, so wie er im Klawiter stand.

> **S11**: Als Forscherin will ich **Nachdrucke und Übersetzungen** eines Werks sehen, um die Publikationsgeschichte zu verfolgen.

> **S12**: Als Nutzerin will ich über **Querverweise** ("Siehe auch") zu verwandten Einträgen navigieren können.

> **S13**: Als Nutzerin will ich den **Inhalt** von Sammelbänden sehen (Inhaltsverzeichnis).

**Daten-Check**:
- Metadaten: title, year, publisher, location, language, pageCount, translator — gut abgedeckt (publisher 56%, translator 42%, rest >80%)
- fullBibliographicEntry: bei allen Einträgen vorhanden
- reprints: 418 Einträge (8.8%)
- translations: 177 Einträge (3.7%)
- contentItems: 936 Einträge (19.7%)
- seeAlso: 683 Einträge (14.4%)

---

## Export & Teilen

> **S14**: Als Bibliothekarin will ich einen Eintrag als **BibTeX oder RIS** exportieren, um ihn in meine Literaturverwaltung zu importieren.

> **S15**: Als DH-Forscherin will ich einen Eintrag als **JSON-LD** herunterladen, um ihn in meinem Linked-Data-Workflow zu verwenden.

> **S16**: Als Nutzerin will ich einen **Permalink** zu einem Eintrag kopieren und teilen können.

> **S17**: Als DH-Forscherin will ich den **gesamten Datensatz** als JSON-LD herunterladen.

**Daten-Check**: JSON-LD-Export existiert bereits. BibTeX/RIS wird client-seitig aus den Feldern generiert. Permalink = `#entry={pageId}`.

---

## Statistiken: Analysieren

> **S18**: Als DH-Forscherin will ich die **Verteilung nach Jahrzehnt** sehen, um Publikationswellen zu erkennen.

> **S19**: Als Forscherin will ich die **Sprachverteilung** sehen, um die globale Zweig-Rezeption zu verstehen.

> **S20**: Als Forscherin will ich auf einen **Statistik-Wert klicken**, um die dahinterliegenden Einträge zu sehen.

**Daten-Check**: year (93.2% Coverage), language (41 Sprachen), entryType, timePeriod — alles berechenbar aus den Daten. Klick-zu-Filter ist reine UI-Logik.

---

## Seitenstruktur (abgeleitet)

| Seite | Route | Primäre Stories | Charakter |
|-------|-------|----------------|-----------|
| **Startseite** | `#` | S1, S2, S3 | Wiki-Portal: Kategorie-Kacheln + Suche + Intro |
| **Stöbern** | `#type=fiction`, `#q=amok` | S4–S8 | Facettierte Suche mit Ergebniskarten |
| **Eintrag** | `#entry=1234` | S9–S16 | Strukturierte Metadaten + Original + Relationen |
| **Statistiken** | `#stats` | S18–S20 | Charts + Kennzahlen (interaktiv → Stöbern) |

Der Pfad der meisten Nutzerinnen: **Startseite → Kategorie-Klick → Stöbern → Eintrag**
