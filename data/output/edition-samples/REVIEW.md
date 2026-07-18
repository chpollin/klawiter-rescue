# Sichtung Werk/Ausgabe-Segmentierung, Stichproben-Gate 1

## Zweck

Dieses Dokument legt der Editorin die deterministische Segmentierung dreier Multi-Edition-Wikiseiten zur fachlichen Sichtung vor, bevor ein Vollauf über alle mehrfach identifizierten Seiten läuft. Grundlage ist die Werk/Ausgabe-Trennung aus der Modellspezifikation in `knowledge/edition-model.md`, Abschnitt "Zielmodell: Werk/Ausgabe-Trennung", mit dem ID-Schema `klawiter:edition/{pageId}-{jahr}-{laufbuchstabe}` und der Evidenz je Ausgabe als `oa:TextPositionSelector` über Zeichenoffsets im Quelltext. Referenz der Prüfung ist die Handzerlegung derselben Seiten, gegen die die maschinelle Abgrenzung gemessen wird. Die Drafts (`*.draft.json`) sind Rohstand des deterministischen Laufs und bleiben unverändert; gefundene Abweichungen stehen als Befund hier, nicht als Korrektur im Draft.

Segmentiert wird ein Editionsblock je `'''[Jahr]:'''`-Kopfzeile. Verlag und Ort werden aus der Kopfzeile getrennt, wobei der Ort das Segment nach dem letzten Komma ist und Mehrfach-Verlage mit `/` zusammenbleiben. Auflagen-Angaben (`*Nte edition ... Jahr`) sind per Modell Unterzeilen der jeweiligen Ausgabe und erhalten keinen eigenen Ausgaben-Knoten. Vorkommen des Werks in Sammelbänden erhalten künftig `schema:isPartOf` und ebenfalls keinen Ausgaben-Knoten.

## Seite 4916, Schachnovelle (Volume)

25 segmentierte Ausgaben.

| ID | Jahr | Verlag | Ort | Seiten | Flags |
|----|------|--------|-----|--------|-------|
| 4916-1942-a | 1942 | Verlag Pigmalión | Buénos Aires | 97 | |
| 4916-1942-b | 1942 | Verlag János Peter Kramer | Buenos Aires | 97 | |
| 4916-1943-a | 1943 | Bermann-Fischer Verlag | Stockholm | 117 | |
| 4916-1950-a | 1950 | Hirschsprung Forlag | København/Copenhagen | 76 | |
| 4916-1950-b | 1950 | Uitgeverij J. M. Meulenhoff | Amsterdam | 94 | |
| 4916-1951-a | 1951 | S. Fischer Verlag | Frankfurt am Main | 94 | |
| 4916-1951-b | 1951 | H. Aschehoug & Co. (W. Nygaard) | Oslo | 61 | |
| 4916-1960-a | 1960 | W. W. Norton & Company, Inc. | New York | 82 | |
| 4916-1962-a | 1962 | Methuen Publishing Ltd | London | 82 | |
| 4916-1966-a | 1966 | C(arl) Bertelsmann Verlag, Gütersloh / Europäischer Buch- und Phonoklub, Stuttgart / Buchgemeinschaft Donauland | Wien | | |
| 4916-1968-a | 1968 | Éditions Payot | Lausanne | 78 | |
| 4916-1969-a | 1969 | C(arl) Bertelsmann Verlag | Gütersloh | 124 | |
| 4916-1974-a | 1974 | Fischer Taschenbuch Verlag | Frankfurt am Main | 94 | |
| 4916-1976-a | 1976 | Európa Könyvkiadó | Budapest | 169 | |
| 4916-1979-a | 1979 | Fischer Taschenbuch Verlag | Frankfurt am Main | 126 | |
| 4916-1992-a | 1992 | Fischer Taschenbuch Verlag | Frankfurt am Main | 109 | |
| 4916-1995-a | 1995 | S. Fischer Verlag | Frankfurt am Main | | |
| 4916-1995-b | 1995 | S. Fischer Verlag | Frankfurt am Main | 109 | |
| 4916-2003-a | 2003 | RM Buch und Medien Vertrieb + Der Club Bertelsmann, Gütersloh / Buchgemeinschaft Donauland | Wien | 109 | |
| 4916-2003-b | 2003 | K. G. Saur Verlag GmbH | München | 100 | |
| 4916-2015-a | 2015 | Alfred Kröner Verlag | Stuttgart | 163 | |
| 4916-2016-a | 2016 | Aionas Verlag | Weimar | 52 | |
| 4916-2016-b | 2016 | Knesebeck GmbH & Co. Verlag | München | 120 | |
| 4916-2016-c | 2016 | Philipp Reclam jun. GmbH & Co. KG | Stuttgart | 107 | |
| 4916-2019-a | 2019 | Nikol Verlag | Hamburg | 76 | |

Nicht als Ausgaben segmentierte Sektionen dieser Seite:

- Contents (zweimal, zur Ausgabe 2015 und 2016-c) und Anhang (zweimal). Inhalts- und Anhangsverzeichnisse der jeweils vorangehenden Ausgabe, keine eigenen Ausgaben.
- Photographs. Bildverzeichnis zur Ausgabe 2016-c, keine Ausgabe.
- Some excerpts. Auszüge der Schachnovelle in Zeitschriften und Anthologien. Vorkommen in fremden Trägerwerken, über `schema:isPartOf` an das Werk zu binden, keine Ausgaben dieser Seite.
- Related topics. Karikaturen und Sekundärvorkommen, keine Ausgaben.
- Translations. Übersetzungen als Verweise auf eigene Wikiseiten (`[[Xake nobela]]`, `[[Novel.la d'escacs]]` usw.). Diese liegen als eigene Volume-Seiten vor und werden dort als Ausgaben modelliert, hier nur referenziert.

## Seite 56, Die Welt von Gestern. Erinnerungen eines Europäers

20 segmentierte Ausgaben.

| ID | Jahr | Verlag | Ort | Seiten | Flags |
|----|------|--------|-----|--------|-------|
| 56-1942-a | 1942 | Bermann-Fischer Verlag | Stockholm | 493 | |
| 56-1947-a | 1947 | Suhrkamp Verlag | Frankfurt am Main | 499 | |
| 56-1952-a | 1952 | S. Fischer Verlag | (fehlt, Feldfehler) | 394 | ohne-ort |
| 56-1952-b | 1952 | Büchergilde Gutenberg | Wien | 394 | |
| 56-1953-a | 1953 | G. B. Fischer Verlag | Frankfurt am Main/Hamburg | 394 | |
| 56-1959-a | 1959 | Ex Libris Verlag | Zürich | 431 | |
| 56-1960-a | 1960 | Bertelsmann Verlag | Gütersloh | 474 | |
| 56-1962-a | 1962 | G. B. Fischer Verlag | Frankfurt am Main/Hamburg | 394 | |
| 56-1964-a | 1964 | Deutscher Bücherbund | Stuttgart/Hamburg | 504 | |
| 56-1968-a | 1968 | Büchergilde Gutenberg | Frankfurt am Main/Wien/Zürich | 504 | |
| 56-1970-a | 1970 | Fischer Bücherei | Frankfurt am Main/Hamburg | 317 | |
| 56-1978-a | 1978 | S. Fischer Verlag | Frankfurt am Main (Feldfehler, Residuum) | 394 | |
| 56-1981-a | 1981 | Deutscher Bücherbund | Stuttgart/Hamburg/ München | 495 | |
| 56-1981-b | 1981 | S. Fischer Verlag | Frankfurt am Main (Feldfehler, Serienresiduum) | 494 | |
| 56-1981-c | 1981 | S. Fischer Verlag | Frankfurt am Main | 494 | |
| 56-1981-d | 1981 | Aufbau Verlag | Berlin/Weimar | 509 | |
| 56-1982-a | 1982 | Ex Libris Verlag | Zürich | 496 | |
| 56-2010-a | 2010 | Fischer Taschenbuch Verlag | Frankfurt am Main | | |
| 56-2013-a | 2013 | Suhrkamp-Insel Verlag | Berlin | 500 | |
| 56-2017-a | 2017 | S. Fischer Verlag | Frankfurt am Main | 700 | |

Nicht als Ausgaben segmentierte Sektionen dieser Seite:

- Contents (dreimal). Inhaltsverzeichnisse der jeweils vorangehenden Ausgabe.
- Anhang. Editorischer Apparat der Ausgabe 2017 (Kommentar, Nachwort, Register), keine Ausgabe.
- Original Manuscripts. Nachweise der überlieferten Handschriften und Typoskripte (Library of Congress, Jewish National and University Library, Lilly Library), keine Ausgaben.
- Excerpts. Sehr großer Block mit Auszügen der Welt von Gestern in Anthologien, Zeitschriften und Lesebüchern. Vorkommen in fremden Trägerwerken, über `schema:isPartOf` an das Werk zu binden, keine Ausgaben dieser Seite.

## Verifikationsbefund

### Blockabgrenzung (gegen die Handzerlegung)

- Seite 4916: 25 von 25 `'''[Jahr]:'''`-Kopfzeilen erfasst. Jeder Editionsblock beginnt am Header und endet vor dem nächsten Header bzw. der nächsten Sektion. Kein verpasster, kein doppelt erfasster Block. Die Offsets `evidence.start`/`evidence.end` stimmen; `text[start:end]` beginnt in jedem Fall mit der Kopfzeile.
- Seite 56: 20 von 20 Kopfzeilen erfasst, gleiche Prüfung bestanden. Kopfzeilen ohne schließende `'''` (1981-b, 1981-c, 1981-d) und die Kopfzeile mit Punkt statt Doppelpunkt nach dem Jahr (2010, `'''[2010]. ...`) wurden trotzdem korrekt als Editionsblöcke erkannt, weil der Zeilenparser nur auf `^'''\s*\[` prüft und nicht auf die schließende Markierung.
- Seite 54, Ungeduld des Herzens, ist handverifiziert, 31 von 31 Blöcken korrekt (nicht Teil dieser maschinellen Nachprüfung, hier als Referenzwert geführt).

Keine der drei Seiten enthält eingerückte Kopfzeilen oder Kopfzeilen mit Punkt statt Doppelpunkt, die verpasst worden wären. Die eine Punkt-Variante (2010) fällt in den vom `parse_header`-Muster `[:.]?` abgedeckten Fall und ist korrekt zerlegt.

### Feldwerte

Seite 4916, keine Feldfehler. Stichproben bestätigt:

- 4916-1966-a und 4916-2003-a behalten die Mehrfach-Verlage mit `/` im Verlagsfeld und tragen den Ort nach dem letzten Komma (Wien). Korrekt nach Regel.
- Seitenzahl je Block aus dem ersten `Np.`-Vorkommen des Blocks. Für 4916-1943-a (117p.) korrekt, obwohl der Block eine spätere Auflage mit `183p.` enthält; die 117 der Erstausgabe steht zuerst und wird genommen.

Seite 56, drei Feldfehler in der Ort-Trennung, alle mit derselben Ursache in der Kopfzeilen-Zerlegung, nicht in der Blockabgrenzung:

1. 56-1952-a, Offset 671. Kopfzeile `'''[1952]: S. Fischer Verlag. Frankfurt am Main''' [S. Fischer Bibliothek]`. Zwischen Verlag und Ort steht ein Punkt statt eines Kommas, und die `'''`-Markierung schließt vor `[S. Fischer Bibliothek]`. Die Ort-Trennung sucht das letzte Komma, findet keines und legt den ganzen Rest ins Verlagsfeld (`S. Fischer Verlag. Frankfurt am Main''' [S. Fischer Bibliothek]`), Ort bleibt leer, Flag `ohne-ort`. Korrekt wären Verlag `S. Fischer Verlag`, Ort `Frankfurt am Main`, Reihe `[S. Fischer Bibliothek]`.
2. 56-1978-a, Offset 2789. Kopfzeile `'''[1978]: S. Fischer Verlag, Frankfurt am Main''' Special edition`. Der Text nach der schließenden `'''` (`Special edition`) und die `'''` selbst landen im Ort-Feld (`Frankfurt am Main''' Special edition`). Korrekt wäre Ort `Frankfurt am Main`, der Zusatz `Special edition` gehört in eine Beschreibung.
3. 56-1981-b, Offset 3151. Kopfzeile `'''[1981]: S. Fischer Verlag, Frankfurt am Main [Gesammelte Werke in Einzelbänden]` ohne schließende `'''`. Das Serien-Residuum `[Gesammelte Werke in Einzelbänden]` steht im Ort-Feld (`Frankfurt am Main [Gesammelte Werke in Einzelbänden]`). Korrekt wäre Ort `Frankfurt am Main`, Reihe `[Gesammelte Werke in Einzelbänden]`.

Diese drei Fälle sind Kopfzeilen-Reinigungsfehler und keine Segmentierungsfehler. Die Blockgrenzen und die Zuordnung Block-zu-Ausgabe sind in allen drei Fällen richtig. Die fehlende schließende `'''` bzw. der Punkt statt Komma sind Quelltext-Varianten, die die Ort-Trennung heute nicht abfängt; ihre Behandlung gehört in eine gehärtete `parse_header`-Stufe vor dem Vollauf.

### Auflagen und die 63-gegen-20-Frage bei Welt von Gestern

Der flache Datensatz führt für Seite 56 dreiundsechzig verschiedene vierstellige Jahreszahlen; segmentiert werden zwanzig Ausgaben aus sechzehn verschiedenen Kopfzeilen-Jahren. Die Differenz ist erklärt und korrekt keine eigenen Ausgaben-Knoten:

- Fünfundzwanzig Jahre stammen aus Auflagen-Unterzeilen `*Nte edition ... Jahr` innerhalb der Editionsblöcke (etwa 1943, 1944, 1946, 1955, 1958, 1990, 2001, 2005, 2011). Auflagen sind Nachdrucke einer bestehenden Ausgabe und per Modell deren Unterzeilen, nicht eigene Ausgaben.
- Die übrigen Jahre stammen aus dem Excerpts-Block (Erscheinungsjahre fremder Anthologien und Zeitschriften, in denen Auszüge abgedruckt sind) und aus Fließtext und Annotationen (biographische und werkgeschichtliche Jahreszahlen wie 1819, 1900, 1914, 1933). Beide sind keine Ausgaben der Welt von Gestern.

Der Befund bestätigt die Tiefenentscheidung des Modells, Auflagen als Unterzeilen zu führen, für diese Seite als sachlich richtig.

## Befund Seite 6820, Schachnovelle (VIST)

Seite 6820 trägt im Kopf `'''Note:''' VIST = Volumes / Individual Stories / Translations` und listet Vorkommen der Schachnovelle in fremden Sammelbänden (`[[Ausgewählte Werke]] [Düsseldorf, 1960 / Zürich, 1964]`, `[[Meistererzählungen]] [Frankfurt am Main, 1970 and 2006]` usw.) sowie Übersetzungen. Sie enthält keine einzige `'''[Jahr]:'''`-Editionskopfzeile. VIST-Seiten sind Vorkommens-Listen, keine Ausgaben-Seiten. Ihre Einträge werden künftig über `schema:isPartOf` an die jeweiligen Sammelbände gebunden, nicht über `workExample` als Ausgaben ausgewiesen. Die Ausgaben-Seite der Schachnovelle ist die Volume-Seite 4916. Seite 6820 verweist selbst darauf (`'''See:''' [[Schachnovelle / Volume]]`).

## Der Editorin vorzulegende Tiefenentscheidungen

Aus der Modellspezifikation, Abschnitt "Tiefenentscheidungen", stehen zwei Modellierungsfragen an, die die Segmentierung nicht selbst entscheidet.

1. Auflagen-Unterzeilen. Die Auflagen-Angaben `*Nte edition ... copies ... Jahr` innerhalb eines Editionsblocks als eigene Knoten mit `schema:bookEdition` modellieren oder zunächst als strukturierte `schema:description` an der Ausgabe halten und die Feingranularität später ziehen. Betroffen auf diesen Seiten unter anderem die Fischer-Taschenbuch-Ausgabe 4916-1974-a mit rund vierzig Auflagen von 1974 bis 1996 und die Ausgabe 56-1981-b mit sechs Auflagen von 1981 bis 2010.
2. Sammelband-Vorkommen. Erscheint das Werk innerhalb eines Sammelbands (die Excerpts- und Translations-Sektionen, die gesamte VIST-Seite 6820), ist das über `schema:isPartOf` von der Ausgabe auf den Sammelband auszudrücken. Offen ist, wie weit die Sammelband-Knoten selbst ausmodelliert werden.

Als konkrete Flag-Fälle zur Entscheidung, wie mit Sonderformen der Kopfzeile umzugehen ist:

- Doppel-Header. Der Segmentierer zerlegt eine Kopfzeile der Form `'''[1960]: A, B / [1964]: C, D'''` an `/` vor `[Jahr]` in zwei Ausgaben und setzt das Flag `mehrdeutiger-header`. Auf den drei Stichprobenseiten tritt dieser Fall nicht auf; die Entscheidung ist für den Vollauf vorzuhalten, wo solche Kopfzeilen vorkommen, und legt fest, ob eine so zusammengeschriebene Kopfzeile stets zwei Ausgaben ergibt.
- ca.-Jahre. Kopfzeilen der Form `'''[ca. 1939]:'''` erhalten das Flag `jahr-unsicher` und tragen das ungefähre Jahr in den Laufbuchstaben-Anker ein. Auf den drei Stichprobenseiten tritt auch dieser Fall nicht auf; zu entscheiden ist, ob das ca.-Jahr die ID prägt oder die Ausgabe einen jahrlosen Anker erhält.
- Ort fehlt oder trägt Residuum. Die drei Welt-von-Gestern-Fälle oben (Punkt statt Komma, Text nach schließender `'''`, fehlende schließende `'''`) zeigen, dass die Kopfzeilen-Zerlegung vor dem Vollauf gehärtet werden muss. Ob solche Fälle automatisch bereinigt oder der Editorin einzeln vorgelegt werden, ist zu entscheiden.

## Messgröße

Die Spezifikation misst den Anteil korrekt abgegrenzter Blöcke gegen die Handzerlegung. Ist-Werte dieser Prüfung:

- Blockabgrenzung: Seite 4916 25/25, Seite 56 20/20, Seite 54 (handverifiziert) 31/31. Zusammen 76/76 Blöcke korrekt abgegrenzt, 100 Prozent.
- Feldreinheit der Kopfzeilen-Felder Verlag/Ort: Seite 4916 25/25 sauber, Seite 56 17/20 sauber (drei Ort-Fehler, siehe Befund). Die Feldreinheit ist von der Blockabgrenzung getrennt zu zählen, weil die drei Fehler in der Kopfzeilen-Zerlegung liegen und die Blockgrenzen nicht berühren.

Die Blockabgrenzung ist damit auf den Stichprobenseiten vollständig. Der verbleibende Handlungsbedarf vor dem Vollauf liegt in der Kopfzeilen-Feldtrennung, nicht in der Segmentierung selbst.
