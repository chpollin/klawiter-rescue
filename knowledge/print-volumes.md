---
title: "Klawiter print volumes: structure, conventions and reference system"
status: draft
language: en
created: 2026-10-23
updated: 2026-10-23
related: [data, pipeline, about, status]
---

# Klawiter print volumes: structure, conventions and reference system

Randolph J. Klawiter compiled the Stefan Zweig bibliography twice, as printed volumes and as the MediaWiki that the production run rescues. Which statements exist only in print, only in the wiki or in both is not known. This document records how the three PDF files of the print volumes are built, which conventions their entries follow, how the compiler's reference system works and what a parser has to expect. It is the basis for turning the volumes into structured data that can be compared with the wiki. That work is a separate strand of the repository and does not touch the production run. The wiki/print merge that [About](about.md) lists as a later option depends on its results.

The structural statements below come from three surveys on 2026-10-23, one per file, which extracted every line with coordinates and font runs through `pdfplumber`. A second round of agents checked each chapter schema independently against the PDFs, and the main agent spot-checked central claims of both rounds.

## The three files

| File | Volume | Pages | What the file is |
|---|---|---|---|
| `I Bibliography.pdf` | Stefan Zweig. An International Bibliography, Ariadne Press, 1991 | 971 | revised production file of the main volume, without front matter, with later insertions |
| `II Addendum I.pdf` | Addendum I, Ariadne Press, 1999 | 481 | complete volume with title, preface, contents, errata, abbreviations and indexes |
| `III Addendum II.pdf` | Addendum II | 1425 | the compiler's working file, without front matter, ending in a compiled tail and a letter |

The files come from the repository `chpollin/SZD`, folder `klawiter/`, commit `58234e73`, and lie in `data/print/`. Their SHA-256 values begin `9556c474…` (main volume), `d4b36ed9…` (Addendum I) and `a3de9c35…` (Addendum II) and match the SZD copies. `pipeline/print_volumes/sections.json` carries these prefixes, and the extraction refuses a file that does not match.

None of the files is a clean copy of a printed book. The main volume starts directly with the divider of section A. The printed book has xvii pages of front matter and 934 pages of text according to the catalogue of the Deutsches Literaturarchiv Marbach, and the errata of Addendum I cite those front pages ("Page xvi Add: GM = …"), so contents, introduction and abbreviation list of 1991 are missing from the file. The publisher describes the book as "17 divisions covering all of the works by and about Zweig in 57 languages", which matches sections A to Q of the file. The file also carries insertions dated up to 2001, for instance a 1993 edition and a 1996 auction note in C 6, and some corrections that Addendum I lists as errata are already applied. It is therefore a later state of the main volume, not the 1991 print. The project has no access to a printed copy. Addendum II has no title, contents or preface. Its last pages hold a list of informants and a letter of 17 August 2009 in which the compiler writes "Currently I am preparing a second addendum to my 'Stefan Zweig. An International Bibliography' [Riverside, CA.: Ariadne Press, 1991. Addendum I, 1999]". Addendum II was never published, so the working file is its only form.

The files stay out of version control (`.gitignore`), because the volumes are presumably protected works of the compiler and the files together amount to about 155 MB, with Addendum II close to the 100 MB per-file limit of GitHub. A working copy is restored from the SZD repository and checked against the hashes above.

## Technical properties

All three files carry a born-digital text layer set in Times New Roman 12 pt, and none contains raster images, so neither OCR nor HTR is required. None is a tagged PDF, none has bookmarks, and none carries internal link annotations. Addendum II contains 15 external URLs that the producing software linked automatically from entry text. Every heading, entry boundary and reference therefore exists only as typography, position on the page and textual convention.

Font size never marks a level. Hierarchy is carried by bold, italic, capitals, the x-position of a line and vertical gaps. The files were produced in WordPerfect, and characters set in its substitute fonts (WP-MultinationalA, WP-MathA, WP-BoxDrawing and others) extract wrongly. Slavic and other diacritics appear as U+FFFF, as `\x00`, as wrong ASCII stand-ins (`ć` as `æ`, `č` as `è`, `š` as `#` in the Addendum I indexes) or as box-drawing characters. This affects field values rather than entry boundaries, and part of it cannot be repaired from the PDF at all.

`pdftotext -layout` is unsuitable as the parsing base. It shifts continuation lines to column 0 after a page break, desynchronises number columns and two-column tables, and places some entry numbers beside the wrong line. Coordinate extraction keeps all of these intact.

## What the volumes say about themselves

The compiler explains his conventions only in scattered notes. Addendum I is the one volume whose front matter survives, and its notes also describe the main volume.

The preface of Addendum I (PDF p. 2) states the basic procedure.

> As in the Bibliography, so also in this Addendum, certain basic procedures have been followed: Names and titles have been quoted in the original language, whereas all subsequent explanatory data have been rendered in English; when referring to periodicals, the basic format includes the volume number, the issue number, the date and then the pagination; references to newspapers generally refer merely to the date in question; wherever I have deemed it pertinent, I have also included certain cross references.

The note on its abbreviations page (PDF p. 12) defines the periodical format and the section codes.

> Where pertinent, the Volume/Jahrgang or Band/Année numbers are given first in Arabic numbers; the issue or Heft numbers are given next, also in Arabic numbers; dates are rendered as follows: day / month / year; page numbers are then added whenever possible [e.g. 16:4 (15 May 1930), 22-29]. The individual entries, such as "AA1", read as follows: The first "A" = Reference to Section A in the 1991 bibliography; the following "A1" = Addendum No. 1.

The headnote of section AA2 (PDF p. 1) adds the German exception for edition data.

> Nota bene: As far as I have been able to do so, I have rendered all names and titles in the original languages, whereas all explanatory data are generally expressed in English. The published volumes of Zweig's works constitute an exception to this rule since in them I have opted to use the following German designations: "Tsd." [= thousand] and "Expl." [Exemplare = copies] as well as "Auflage" [printing/impression], all of these with reference to the number of volumes published and the impressions thereof.

The preamble of section H in the main volume (PDF p. 290) explains its ordering.

> the entries have, wherever possible, been alphabetized by subject matter rather than by the titles of the individual essays. Thus, "Abschied von Rilke" and other Rilke-related essays/reviews are to be found under RILKE, RAINER MARIA. The main entries for book reviews will be found under the authors of the volumes rather than under their titles. […] When the subject matter does not entail the name of a person, that entry is listed alphabetically by the title of the essay itself.

Further notes in the main volume say that section M lists reviews of the German editions and their translations (p. 698), that section L mostly omits encyclopedia and literary-history references (p. 520), that a bold number in Index A marks an entry with cross-references to reprints or translations of that number, and that Index C excludes excerpts, editions, reprints and translations. Section KA1 in Addendum I notes that the compiler transcribed letters from auction catalogues without marking Zweig's errors with "(sic)" (p. 134).

## Section scheme

All three volumes share one section scheme. A letter names the section in the main volume, and the addenda append `A1` or `A2`. The table gives the section titles as the files set them.

| Letter | Main volume (1991) | Addendum I (1999) | Addendum II |
|---|---|---|---|
| A | Collected Works | AA1 Collected Works | AA2 Collected Works and Selected Works, German |
| B | Selected Works | BA1 Selected Works | BA2 Collected and Selected Works in translation |
| C | Essays and Lectures in Bookform | CA1 Essays/Lectures in Book Form | CA2 Essays in Book Form |
| D | Poetry | DA1 Poetry | DA2 Poetry |
| E | Dramas | EA1 Dramas | EA2 Dramas |
| F | Fiction | FA1 Fiction | FA2 Fiction |
| G | Historical and Biographical Studies | GA1 Historical Studies and Biographies | GA2 Historical Studies |
| H | Essays, Lectures, Reviews and Excerpts from the Historical and Biographical Studies | HA1 Essays, Lectures, Reviews | HA2 Essays |
| I | Translations | IA1 Translations | IA2 Translations |
| J | Forewords and Afterwords | JA1 Forewords and Afterwords | JA2 Forewords and Afterwords |
| K | Correspondence | KA1 Correspondence | KA2 Correspondence |
| L | Secondary Literature I and II | LA1 Secondary Literature | Secondary Literature, without heading code, cited as LA2 |
| M | Reviews | MA1 Reviews | Advertisements for Works by Zweig, cited as MA2 |
| N | Film Versions of Zweig's Works | NA1 Stage Productions, Movies | none |
| O | Zweig's Works Set to Music | OA1 Works Set to Music | none, poems set to music stand in DA2 |
| P | Zweig Symposia, Centennial 1981 | PA1 Symposia and Exhibitions 1992–1996 | P section 1981 and Symposia and Exhibitions 1981–2009, cited as PA2 |
| Q | Works Dedicated to Zweig | QA1 Works Dedicated to Zweig | none |
| R | none | RA1 Handwritten Dedications | none |
| Indexes | A Proper Names, B Artists, C Chronology, D Languages other than German, E Newspapers and Periodicals | A Works by Zweig, B Themes, C Sources, D Proper Names | none |
| Supplement | Additional Information as of September 1990 | Errata to the main volume, before the sections | none |

The page ranges of the main volume were reconstructed from divider pages and running heads and confirmed by an independent check of every boundary.

| Part | PDF pages | Part | PDF pages |
|---|---|---|---|
| A Collected Works | 1–19 | J Forewords and Afterwords | 420–431 |
| B Selected Works | 20–22 | K Correspondence | 432–518 |
| C Essays and Lectures in Bookform | 23–32 | L Secondary Literature I | 519–619 |
| D Poetry | 33–66 | L Secondary Literature II | 620–696 |
| E Dramas | 67–78 | M Reviews | 697–732 |
| F Fiction | 79–160 | N Film Versions | 733–740 |
| G Historical and Biographical Studies | 161–288 | O Works Set to Music | 741–743 |
| H Essays, Lectures, Reviews | 289–398 | P Symposia 1981 | 744–748 |
| I Translations | 399–419 | Q Works Dedicated to Zweig | 749–752 |
| Index A Proper Names | 753–916 | Index D Languages | 924–929 |
| Index B Artists | 917–918 | Index E Periodicals | 929–970 |
| Index C Chronology | 919–924 | Additional Information as of September 1990 | 970–971 |

The file ends inside the last part, so that part may be incomplete.

The page ranges of Addendum I were taken from entry numbers, the contents of the volume and the index headings, and confirmed by an independent check. Each section is announced by a placeholder page carrying only "Graphic Page (n) XA1 / TITLE", which presumably stands in for an illustrated divider of the printed book.

| Part | PDF pages | Part | PDF pages |
|---|---|---|---|
| Title, preface, contents | 1–5 | JA1 Forewords and Afterwords | 127–128 |
| Errata to the main volume | 6–11 | KA1 Correspondence | 130–214 |
| Abbreviations | 12–15 | LA1 Secondary Literature | 216–361 |
| AA1 Collected Works | 17 | MA1 Reviews | 363–391 |
| BA1 Selected Works | 19–24 | NA1 Stage Productions, Movies | 393–404 |
| CA1 Essays in Book Form | 26–30 | OA1 Works Set to Music | 406 |
| DA1 Poetry | 32–36 | PA1 Symposia and Exhibitions | 408–415 |
| EA1 Dramas | 38–41 | QA1 Works Dedicated to Zweig | 417 |
| FA1 Fiction | 43–64 | RA1 Handwritten Dedications | 419–422 |
| GA1 Historical Studies | 66–85 | Index A Works by Zweig (A1–A7) | 423–440 |
| HA1 Essays | 87–123 | Index B Themes | 441–444 |
| IA1 Translations | 125 | Index C Sources (C1, C2) | 444–456 |
| | | Index D Proper Names | 457–481 |

The page ranges of Addendum II were reconstructed from its headings and confirmed by an independent check. The file has no printed page numbers apart from running heads on the symposia pages, which appear to be carried over from section P of the main volume.

| Part | PDF pages | Part | PDF pages |
|---|---|---|---|
| AA2 Collected and Selected Works, German | 1–32 | Secondary Literature, German, unheaded | 805–1237 |
| BA2 Collected and Selected Works in translation | 33–117 | Secondary Literature by language | 1238–1388 |
| CA2 Essays in Book Form | 118–160 | Advertisements for Works by Zweig (MA2) | 1388–1392 |
| DA2 Poetry | 161–257 | P Zweig Symposia, Centennial 1981 | 1393–1397 |
| EA2 Dramas | 258–269 | "Zweig Bibliography / English" | 1398–1408 |
| FA2 Fiction | 270–497 | Advertisements, duplicate | 1408–1413 |
| GA2 Historical Studies | 498–613 | Zweig Symposia and Exhibitions (PA2) | 1413–1422 |
| HA2 Essays | 614–773 | Zweig on the Internet, Abbreviations | 1423–1424 |
| IA2 Translations | 774 | Letter of 17 August 2009 | 1424–1425 |
| JA2 Forewords and Afterwords | 775–778 | | |
| KA2 Correspondence | 779–804 | | |

Within the secondary literature, the alphabetical "BOOKS, ARTICLES AND REVIEWS" (808–1233) is followed by "EXHIBITIONS, FILMS, LECTURES, READINGS, THEATER PRODUCTIONS, ETC." (1233–1237). The language sections run over many languages, about forty in FA2, thirty-six in GA2 and thirty-two in the secondary literature.

Within LA1, the German subdivisions follow the volume's contents exactly by entry number (frequently cited volumes 1–15, books and periodical articles 16–386, newspaper articles 387–650, radio and television 651–667, lectures 668–674, manuscripts 675–689, then a block of reviews), and the other languages run from Albanian (690) to Yiddish (1061–1063).

Section titles differ between table of contents, running heads and divider pages within one volume, for instance EA1 "Dramas" and "Dramas and Scenarios". The page numbers in the contents of Addendum I drift by up to seven pages from the body, while its entry-number ranges match exactly, so entry numbers are the reliable locator. Printed page numbers and PDF page numbers diverge in every file, because blank and divider pages are missing from the PDFs. Addendum II carries no printed page numbers before its tail.

## Levels below the section

Below the section the volumes use the same kinds of units, marked differently in each file.

| Unit | Main volume | Addendum I | Addendum II |
|---|---|---|---|
| Section divider | divider page with letter and title | placeholder page "Graphic Page (n) XA1 / TITLE", otherwise only running heads | capital line at page top, such as "FA2 / FICTION" |
| Sub-genre or part | Arial bold mixed case (B–E) or Times bold capitals (F, K, L, M), e.g. "Collected Poems", "INDIVIDUAL LETTERS" | bold capitals | mostly bold capitals, e.g. "VOLUMES", "INDIVIDUAL STORIES", "EXCERPTS", "POEMS SET TO MUSIC" |
| Language | bold capitals or Arial bold, alphabetical | bold capitals, German first without heading | mostly bold capitals, German first without heading except in AA2 |
| Work heading | roman capitals in G (e.g. AMERIGO, BALZAC) with "* * * * *" separators, Arial bold in E with an unnumbered commentary paragraph | bold capitals with bracketed references in MA1 | none, work-centred entries instead |
| Preamble or note | flush paragraph headed "Secondary Literature:" or "NB:" | "NB:" paragraphs | "Nota bene", "NB:" |
| Numbered entry | number at the left margin, text with hanging indent | bold number at the left margin, hanging indent | running numbers only in AA2, DA2 and the symposia list |
| Cross-reference stub | `****` | `*` | `***` in DA2, otherwise short "See" entries |
| Sub-item | `[1]. [2].`, `Vol. n.` | `[1].`, `[a]`, `Vol. I.` | `[1].`, `[X].`, `[a]`, `Vol. n.` |

The main volume also contains collection headers in section A, an unnumbered series title with a descriptive paragraph followed by the volumes as numbered entries, and "ADDENDUM" headings near the end of sections A, C, F, G, H, J, K and L whose entries continue the section's numbering. Several sections have further levels. E groups its entries under twelve drama work headings with language headings below them, I under translated authors ("BAUDELAIRE, CHARLES: INDIVIDUAL POEMS"), K under "REPOSITORIES", "COLLECTED LETTERS" and "INDIVIDUAL LETTERS", and M under genre headings that mirror sections A to L. G uses roman inline labels such as "Excerpt" and "Individual Historical Miniature" inside its work blocks. Section K has its own table of repository sigla (PDF pp. 433–435).

The preambles headed "Secondary Literature:" in sections B to K are lists of cross-references into L and M, sorted by topic ("Zweig as dramatist see L 132, …", "Reviews M 20-31"). They form a second, topical access to the reference network. In Addendum I, German material always comes first in a section and never carries a heading, so the first language heading marks the switch to translations or foreign secondary literature. In LA1 the foreign languages carry genre headings of their own ("BOOKS AND PERIODICAL ARTICLES", "NEWSPAPER ARTICLES", "REVIEWS" and others, chosen per language), and language and genre headings are typographically identical, so only a vocabulary separates them. MA1 groups its reviews under headings naming the reviewed work with its addresses ("ADAM LUX [E 5 / EA1 1 / NA1 1]"), and each entry runs through languages with labels such as "German:" and "French:".

Addendum II is organised differently in its works sections. FA2, GA2, HA2 and DA2 each split into volume entries and work-centred entries for individual stories, essays, poems or excerpts. A work-centred entry gives the first periodical printing and then a numbered list of every reprint in a collection, each reprint cited by section code, title, year and contents number.

> "Der Amokläufer. Eine Novelle" [1922] in *Neue Freie Presse* … Reprinted as … in [2]. AA2 1 Amok… 1950 [1], pp. (5)-(59). … [23]. LA2 Jacquot…

These lists belong to the bibliography's own record of printing history, and in practice they work as a concordance between works and collections. Earlier sampling had suggested that the volume contains separate registers by work or translator. The surveys found a single topical cluster of cross-references inside the alphabetical essays (PDF pp. 617–618, "Autographs - Collecting and Collections, see: [1]. HA2 …") and no concordance by translator. In the translation subsections of FA2, GA2, HA2 and KA2, the pattern of volumes followed by "INDIVIDUAL STORIES", "INDIVIDUAL ESSAYS" or "INDIVIDUAL LETTERS" recurs under each language.

## Reference system

Every entry has an address formed by section and number, and the volume suffix keeps addresses distinct across the three volumes.

| Volume | Address form | Example |
|---|---|---|
| Main volume | letter and number | `F 47`, `H 370`, `L 1125` |
| Addendum I | letter, `A1` and number, optional letter suffix for inserted entries | `HA1 34`, `FA1 24a` |
| Addendum II | letter, `A2` and number, or code, title and year where entries are unnumbered | `AA2 57`, `FA2 Novelly … 1994` |

Entries refer to these addresses in a fixed notation. The compiler set the links by hand, and the PDFs never made them clickable.

| Notation | Meaning |
|---|---|
| `See F 47`, `See A 48 / C 3` | related entry, groups separated by slashes |
| `Contents: F 1, 6-8 / L 68` | contained works, with ranges |
| `Rep: A 85, Vol. 10, pp. 1-417`, `REP:` | reprint in another entry, with locator |
| `[A 8]` after a title | the work an edition or translation belongs to |
| `[H 370]`, `[Cont. H 367]`, `[Cont. of K 387]` | back-reference from an addendum, or continuation of an earlier entry |
| `[Correction to L 77]` | correction of an earlier entry |
| `See HA1 34[1, 2]`, `K 760 (1)`, `KA1 24[8, No. 3539]` | reference to a sub-item of an entry |
| `AA2 57: Kassette IV [1]`, `No. 6`, `[Nos. 18-22]` | position inside a multi-volume set or collection |
| `BA2/GA2 …`, `[G 224 & 445 = H 48, 143]` | compound or equated references |
| `See Index A1:Heroischer Augenblick`, `See Index D:…` | reference to an index heading (Addendum I) |
| `[See p. 934]`, `[Zh., 681]`, `See Bild, No. 87, p. 91` | page reference or reference to an external source |
| `G 379*` | starred reference, meaning not defined in any of the files |

Not every "See" is a cross-reference. In Addendum I about 160 of them introduce a source citation, such as an auction catalogue or a newspaper. The references also carry typing errors ("H 307, 365365", "[RSJ]"), so their parsing has to tolerate noise.

Because the notation is formal, a parser can resolve each address to its target. A reference to an address that does not exist signals either a segmentation error or an error in the print. The probe of 2026-10-23 (see Probes) resolves almost every internal reference of the main volume and of Addendum I. The residue consists mostly of tokens that only look like addresses, such as page numbers of the Börsenblatt supplement "Aus dem Antiquariat" (`A437`), postal codes, years after a letter ("A 1988 film", "Teilband I 1933") and catalogue numbers of a Chinese series (`[B 21]`). A list such as "Reprinted A 144, 559-573" is ambiguous, because the numbers after the comma may be pages or further addresses. The compiler's explicit correction and continuation markers are rare in the sections; corrections to the main volume stand mainly in the errata pages of Addendum I.

## Print and wiki

The wiki is the latest state of the bibliography. The compiler's own account on wiki page 1140 dates a prototype to December 2008, migrated from the WordPerfect files, and most pages and revisions were created after the letter of August 2009. The wiki contains publications up to 2020, which none of the print volumes can hold.

The wiki cites print addresses (`See F 455`, `HA1 152`, `LA1 229`) and the sigla `[PF]` and `[RJS]`, but the current page text carries them only on a small number of entry pages. Earlier revisions carried them on many more pages, and the compiler's account removed them between 2012 and 2020. An address anchor for the concordance therefore has to be mined from the revision history. A cited address is moreover rarely an identity. In spot checks it pointed to an earlier edition by the same translator (`F 533` on page 564), to a translation pointer without a record of its own, or to the same work with a conflicting imprint, and only for a few entries to the same publication. A cited address is a relation of unknown type and has to be typed before it can serve as evidence for identity. Wiki pages 2101, 2154 and 2155 transcribe the contents of 1991 and the section breakdowns of both printed volumes with entry ranges and printed page numbers. These findings come from a read-only agent survey of the raw wiki revisions on 2026-10-23, spot-checked by the main agent.

Three overlap experiments on small seeded samples (2026-10-23, one agent reader, not human-checked, outside the benchmark pages) sharpen this picture.

- Text form. Addendum II and the early wiki share one text source: its matched wiki pages were created in 2009 to 2011 and are near-verbatim, down to a missing space. Main-volume and Addendum I entries were re-keyed and normalised (periodical sigla spelled out, dates written in full, no addresses or sigla), and their first wiki revisions date from 2009 to 2020. Character alignment against early revisions is therefore a viable route to identity for Addendum II only. Between 2012 and 2017 the compiler pasted runs of main-volume entries verbatim, with numbers and sigla, and rewrote them within minutes; these short-lived revisions are the only verbatim trace of the main volume.
- Overlap. Of a sample of print entries of the main volume and Addendum I, about half were found in the wiki as a record or as a contents line. Book editions and contributions to books were mostly found, periodical items, auction listings and typescripts mostly not. Of Addendum II, half were found. In the other direction, three in four sampled wiki publications from before 2010 are the same publication in print, often inside a sub-edition list or a collected-series entry; a few have only another edition in print. Print-only records, mostly periodical items, are an expected and valid result.
- Cited addresses. In a sample of addresses cited in wiki revisions none marked the same publication. They mark the translated work of a translation (`[Der Amokläufer. F 1] in …`), containment (`REP: F 289`, a cassette of a collected edition) or a looser relation such as a review. Most were added in 2009 as translation pointers or with the later pastes and are gone from the current text. An address is a work or containment edge, never evidence for identity.
- Keys. Equal title words and year work as a blocking key for book editions but not as a decision. False pairs come from other editions whose year stands in a sub-edition list, from reviews and from same-titled translations; misses come from year conflicts, title typos, author-led titles and series entries. Most print matches are contents lines, which the wiki publication layer does not hold as publications. A candidate needs a second agreeing field (publisher, place, translator or extent) before it can count.

## Entry anatomy

The sections fall into a few entry types.

### Editions of Zweig's works

Sections A to G, I and J, and the volume entries of the addenda describe a work together with its editions. Such an entry is a small tree, which matches the work/edition graph the repository builds for the wiki ([Data](data.md)).

| Element | Example |
|---|---|
| Number | `48` |
| Title, German first editions in bold italic, later entries in capitals | `Encontros`, `BUCHMENDEL` |
| Related work | `[A 8]` |
| Contributors with role | `Trl.` (B–E, Addendum I) or `Tr.` (A, F–Q), `Ed./Aftw.`, `Frw.`, `Intro.`, `Cover design` |
| Printings | `[1.-2. Tsd.]`, `2. Auflage`, `Expl.`, `Sub. eds./imprs.` |
| Extent | `3 vols.`, `vii/229/[1]p.`, `illus.` |
| Imprint | `Porto: Livraria Civilização, 1950` |
| Series | `[Insel-Bücherei, 408]` |
| Further editions | `FIE: [1]. … [2]. …`, `NEW ED:`, in Addendum II `Fischer Editions/Reprints:` and `Non-Fischer Editions/Reprints:` |
| Contents | `Contents:` with addresses or titles |
| Notes | bracketed free text, `[Lic. ed for the German Democratic Republic]` |
| Informant siglum | `[PF]`, `[RJS]` |
| Cross-references | `See …` |

### Contributions and secondary literature

Essays (H), secondary literature (L) and the individual works of the addenda name a person or subject, the title in quotation marks, then `in` with periodical and place, volume and issue, date and pages, followed by labels such as `REV:` for a review written by Zweig, `REP:` for a reprint, `EXC:` for an excerpt and `TRANSLATION(S):`, and close with an informant siglum. In the main volume periodicals often appear as sigla (`NEUFP`, `BERLTB`) that only Index E resolves.

### Letters, reviews, performances and events

Correspondence entries (K) are ordered by correspondent and list holdings as sub-items, each with repository or auction source, extent and dates. Some run over ten PDF pages. Review entries (M) are headed by the reviewed work and list reviews as sub-items, with the language label changing inside one entry in Addendum I. Film, stage and music entries (N, O) give work, medium, place, year and credits. Symposia entries (P) reproduce programmes with numbered talks. Dedication entries (Q, RA1) give author, work and the dedication text.

## Abbreviations and sigla

The abbreviation lists survive only in the addenda. Addendum I (PDF pp. 12–15) has general abbreviations, informant sigla and work-sigla tables that map numbers of the main volume to titles. Addendum II (PDF pp. 1423–1424) has only a list of informants headed "PEOPLE CITED". The main volume lost its list with the front matter, and its own sigla resolve only partly through the other files.

| Kind | Where resolved | Gaps |
|---|---|---|
| General abbreviations (Aftw., EXC, FAC, FIE, Trl., Tsd. …) | Addendum I, PDF p. 12 | `IB` stands both for Insel-Bücherei and for an informant |
| Informant sigla, main volume | mostly through the Addendum I list | `MMW` and `HZ` in none of the files |
| Informant sigla, Addendum I | own list | several sigla used but not listed, e.g. `BVC`, `AMC` |
| Informant sigla, Addendum II | own list | `PF`, `DAP`, `GK` used but not listed, several listed but unused |
| Periodical sigla, main volume | Index E | none observed |
| Repository sigla, letters | table in section K of the main volume | none observed |
| Source abbreviations `Zh.`, `Bild`, `Ol.` | none | defined in the lost front matter of the main volume |
| Section codes | Addendum I, PDF p. 12 | Addendum II undocumented, read by analogy |

The informant lists name private persons and institutions who supplied information. They stay in the source files and in derived research data. This document does not reproduce them.

## Hazards by file

### Main volume

- Entry numbers sometimes extract as two tokens ("5 14" on PDF p. 217).
- Index A (PDF pp. 753–916) is broken in the PDF itself. Long reference strings are drawn one character per line in vertical columns, so the index cannot be recovered from this file. Without a printed copy it can only be rebuilt from the entries.
- Index pagination overlaps, because Index C restarts at printed page 884 inside the range Index A claims.
- The hanging indent varies between sections (108, 122, 144 and 150 pt against a margin of 72 pt), so continuation means "x greater than the margin".
- Entry numbers are mostly bold in A–H but always roman with a letter prefix in E and I–Q, so font is no reliable start criterion. Position and number sequence are.
- Revised regions carry editing debris (PDF p. 105) and two duplicate numbers, C 3 and F 50, both at post-1991 insertions.
- Flush paragraphs whose wrapped lines begin with a number look like entry starts.
- Line-end hyphens before digits are mostly ranges but sometimes split numbers ("11-/51" for L 1151).

### Addendum I

- The errata to the main volume (PDF pp. 6–11) form a single list. Each erratum opens with the printed page of the 1991 book ("Page 21") and names its target by address with an optional locator (`A 5, line 4`, `K 38[2]`), by a label (an index heading, "Obras completas") or not at all. The printed pagination of 1991 drifts against the main-volume file, so targets resolve by address only. The errata replace readings, add, omit, move and renumber entries ("Renumber as H 152a"), reorder two entries and add prose notes, and some correct the front matter and index pages of 1991. `p05_errata.py` reads them as compiler claims.
- Seven entry numbers are missing without a gap in the text. At least one is a numbering slip of the compiler, since KA1 cites "Einige Grundlagen …" as `[HA1 54]` while the text is printed as HA1 55. References to such numbers have to be checked against neighbouring entries before they count as broken.
- The running heads of the indexes name the wrong index and carry frozen page numbers, so index boundaries come from the bold index headings.
- Some entry numbers are split across fonts or glued to the first word ("1040aPinto,"), and bold years at the left margin inside long letter entries look like entry numbers.
- Overprinted háček glyphs split one line into two on a few pages.
- The indexes are set in two columns at 10 pt.

### Addendum II

- The tail after the secondary literature is a compilation. Advertisements for Zweig's works appear twice with practically identical text (PDF pp. 1388–1392 and 1408–1413), the 1981 symposia appear twice, an English list of works without section codes (pp. 1398–1408) follows another scheme, and a stray running head recurs on the last pages.
- Headings do not follow one typographic rule. Most are bold capitals at the left margin, but some are set in regular weight, in mixed case, indented or centred, and many entry titles are bold too, so bold alone identifies no heading. Only the title lines on PDF p. 1 are set at 14 pt.
- Draft flags such as "NEED INFO" and "HAVE INFO / NEED HELP" are set partly in bold capitals and look like headings (GA2 Chinese, PDF pp. 529–536). Query marks ("[1922??]") stand inside entries.
- A faulty search-and-replace turned "Seele" and "seen" into "See:le" and "See:n" on a few lines ("See:lenmeister"), which a reference parser must not read as "See:".
- Numbering inside reprint lists is unfinished. `[X]` marks items without a number, and some lists run non-monotone ("11 12 9 X X X 10").
- Reprint lists in the translation subsections often run one item per paragraph and look like separate entries by layout, although they belong to the preceding work entry.
- Page margins switch between two regimes page by page, and most of the body has no hanging indent, so boundaries depend on vertical gaps and the font of the first run.
- Entries that begin at the top of a page carry no gap information. A bold first run combined with a short, punctuated last line on the previous page decides most of them.

## Entry boundaries

The surveys tested start rules on coordinates. In the main volume and Addendum I, the left-margin position of the number, checked against the number sequence, found every numbered entry except a handful of documented special cases. The remaining irregularities are printed gaps and duplicates, which the rule detects without resolving. In Addendum II, vertical gaps and heading detection decide boundaries within a page reliably. Page-top cases and the attachment of per-paragraph reprint items to their entry need further rules and leave a residue for review.

The figures of the survey of 2026-10-23 describe the files as extracted on that day.

| | Main volume | Addendum I | Addendum II |
|---|---|---|---|
| Numbered entries | 6,329 | 2,320 | about 330 running numbers in AA2, DA2 and the symposia list |
| Unnumbered units | 459 `****` lines | 708 `*` entries | several thousand blocks, entry type set by font and layout |
| Numbering gaps | 15 | 7 | not applicable |
| Duplicate numbers | 2 (C 3, F 50) | none | one run in DA2 (PDF p. 229) |

## Probes

Three deterministic probes in `pipeline/print_volumes/` test the files on the `p01` lines. They write their reports to `data/print/derived/reports/` and need no model call. The figures below are those of the run of 2026-10-23, after an independent agent review of the same day had found several errors in the first run, among them running heads read as entries, numbering insertions counted as duplicates and claims the reports did not support. The corrected code is the source of the figures.

`p01_extract.py` writes every glyph of a page into exactly one line, and a second extraction is byte-identical. The first property holds by construction and guards the code rather than the data. Line grouping depends little on the vertical tolerance: between 2 and 3 pt the line count differs on two pages of the main volume and nine of Addendum I, while at 1 pt lines of the main volume split on about a third of its pages, presumably where substitute glyphs sit on a shifted baseline.

`probe_addresses.py` builds the address census. An entry start is a number, optionally preceded by its code (`L 464`), left of the part's hanging indent and on the longest chain of such numbers rising by at most ten per step. It finds 6,329 entry starts in the main volume, the figure of the earlier survey, with 15 gaps in G and L, and 2,319 in Addendum I, where the apparent duplicates of the first run are insertions with a letter suffix (`NA1 20a`). The highest number per section equals the transcribed contents of 1991 in every section except D, where the contents give 227 and the file ends at 223, and J, where the file runs to 79 against 75; the J entries above 75 stand on the last page of the section, which suggests later additions. MA1 appears to run past its contents only because a line beginning "110 = G 336" joins the chain, and the probe now lists such jumps for review. In Addendum II only AA2, DA2 and the symposia list carry running numbers.

References resolve against these starts to 99.7 percent within the main volume, 99.6 percent within Addendum I and 99.4 percent from Addendum I into the main volume. Almost every unresolved target lies above a section maximum or in a known gap, such as the reference to G 75, which the print replaces by a stub. Resolution therefore confirms the numbering and finds references into gaps, but it cannot detect a wrong boundary between two existing numbers. A content check, comparing the title cited before an address with the opening of the target entry, would test the segmentation itself and is not built yet.

`probe_roundtrip.py` gives every line one role and checks two invariants of the code: the roles rebuild the `p01` page texts, and each section's units reproduce its lines contiguously and in order. It then compares four single-signal boundary rules (number, hanging indent, vertical gap, bold start) per section, drops a rule that carries no signal there, and lets the vertical gap abstain at a page top, where no gap exists. The rules are not independent, since bold and number are only counted at the margin, so their agreement overstates certainty. The comparable figure across files is the number of disputed lines per unit.

| | Main volume | Addendum I | Addendum II |
|---|---|---|---|
| Carrying signals | number, indent, gap. Bold carries no signal from section I on | all four | gap and bold. No hanging indent, numbers only in AA2, DA2 and the symposia |
| Disputed lines per unit | about 0.1, concentrated in E, G, H and K | about 0.02 | about 0.6, GA2 the weakest |

`probe_signatures.py` profiles each unit by its citation forms: imprints, periodical citations, contributions that cite their host volume by address ("in Romans et Nouvelles [BA1 5]"), volumes that give only extent and year because the imprint stands in a collection header, and numbered sub-items outside a Contents list. The review checked a seeded sample of units and found that these patterns miscount often, for instance by taking the imprint of a reviewed book or of a letter holding as a publication, by reading "in" inside a title as a host reference, and by missing imprints with a bracketed place. The shares of units with several citations are therefore no measure of how many publications an entry describes. That an entry can describe several publications is established by direct reading of the files (collected editions with their printings, reprint lists in Addendum II, review entries in M). The bracketed sigla differ per volume: `[PF]` dominates the main volume, informant sigla dominate Addendum I, and in Addendum II brackets mostly hold supplied places such as `[Wien]`.

Four consequences follow for the parse stage. The address grammar is deterministic, and the numbering of the main volume and Addendum I is fully reconstructed, while boundaries between existing numbers still need a content check or the benchmark. Addendum II needs its own boundary rules based on gaps and bold, with a review residue that page tops dominate. An entry can describe several publications, so the record model separates entry and described object. Some entries depend on context outside themselves, a collection header or a host entry, and the parser has to carry that context.

## Benchmark

A held-out sample of pages (`bench_sample.py`, seeded) is annotated blind by two agents, one with the conventions of this document and one with the PDFs only, and `bench_compare.py` scores boundaries, publication counts and references of the method against each annotator and the annotators against each other. The review judged the first sample too small and too little stratified: the largest sections fill the quota, so E of the main volume, NA1 and the numbered parts of Addendum II are missing, and the pages were part of the probe runs before they were held out. A second sample should draw entries or page pairs, oversample hard cases with recorded weights, keep a separate development set and be frozen before results are inspected. Agent annotation does not replace a human gold standard; disagreements and a control sample of agreements need a human decision.

The first run on 28 pages (2026-10-23) gives three results. The two annotators agree on almost every unit boundary and on the publication class (none, one, several) of almost every unit; being two agents of the same kind, their agreement bounds rather than proves correctness. The method finds practically every boundary the annotators set, but sets additional ones: few in the main volume and Addendum I, about a quarter too many in Addendum II. The additional boundaries fall into two classes, numbered sub-items or volume lines on a line of their own ("[5]. CA2 …", "Vol. 2. …") and wrapped continuation lines after a line without closing punctuation ("1966), 307-312 [DAP].", "Review / of: …"). The publication count of probe_signatures.py agrees with the annotators' class for only about three units in five and is not usable as it stands. Annotator A recorded the title references of Addendum II ("FA2 Kaleidoskop 1936"), annotator B did not; the address grammar of the method covers neither. Any rule built from these error classes is tuned on the sample, so its effect has to be measured on a fresh sample.

The rules that followed came from those error classes and from an agent survey of development pages: sub-item openers never start a unit, unnumbered parts of Addendum II break only at vertical gaps, page tops are decided by how the previous page ends, and objects are read from numbered items by the scope of their label. A second sample of 44 pages (`bench/v2`, seeded, hard sections oversampled, disjoint from development pages) was frozen before these rules were scored and annotated blind by two agents. On it the annotators again agree on every boundary and on almost every publication class. An independent review of the milestone (2026-10-23) found three faults in the scorer, all corrected before the figures below: gold units with identical openings were all located on the first matching line, a unit's own printed address was counted as one of its references, and the method's objects and references were counted over the whole unit while the annotators saw only the sampled page. Five regular expressions of the rules also held a control character instead of a word boundary and so never matched; the correction left the scores on the sample unchanged. Measured after these corrections (`data/print/derived/reports/bench_compare_v2.json`), the method finds practically every boundary the annotators set. It sets very few extra ones in the main volume and Addendum I and somewhat under one in ten too many in Addendum II, most of them inside a single double-spaced paragraph that the gap rule reads as separate units; a gap rule that compares with the local line pitch would remove them. A date line ("5 September 1928.") once entered the number chain as an entry number. Reference recall and precision are near complete in all volumes. The publication class agrees with the annotators for roughly two to three units in four. A definition difference explains only part of that gap, since the annotators count later printings with data of their own and every address of an address-only reprint list. The rest are rule gaps: a host volume cited by address without year, unnumbered `REP:` and `EXC:` labels, double counting of "in [1].", further objects named only in prose, and unpublished holdings. Which of these count as objects is a policy question for the operator. `bench_compare.py` lists every disagreement for a human decision. Most are method against both annotators; a small part are splits between the annotators on the publication count. The sample is a single frozen draw annotated by agents, so the figures bound the method's agreement with careful readers on these pages; they are no measured correctness until a person has decided the disagreements.

## Approach

The analysis proceeds in stages, each with an inspectable output.

| Stage | Input and output | Purpose |
|---|---|---|
| `p01 extract` | PDF to lines as JSONL, with volume, page, coordinates, font runs, text and a defect flag, page hashes in its report | lossless deterministic base, running heads and page numbers marked rather than removed |
| `p02 view` | lines to Markdown per volume and section | reading view, derived and regenerable |
| `p03 records` | lines to entry and object records with stable identifiers, unaltered text and hash, heading context, rule-read fields and imprints inherited from collection headers, kept apart from the object's own fields | the records every later claim points back to |
| `bench_sample`, `bench_compare` | frozen page samples and blind annotations to scores and a disagreement list | measured agreement of boundaries, objects and references |
| `p04 wiki revisions` | the dump's main-namespace revisions to one line each, through the readers of the production extraction | the only place where verbatim print text survives in the wiki |
| `p05 errata` | the errata pages of Addendum I to correction claims against main-volume records, with the printed wrong and right readings verbatim | the compiler's own corrections |
| `p06 claims` | records to typed compiler reference claims (See, Rep:, Contents:, Correction to, Cont., work references) with resolved targets, all `proposed` | reference graph and a self-check of the segmentation |
| `p07 concordance` | records and revisions to print-wiki claims on two routes, alignment by distinctive word 5-grams over all revisions and title, year and a second field (imprint, translator, extent or page range) in the latest text or page title, a field match whose wiki line lies inside a publication slice that hashes identically to the published slice names that publication, otherwise only the page; plus a local file of matches per wiki page for the lab view | concordance, with silver pairs from near-verbatim alignment measuring what the field route loses |
| `p08 field check` | silver pairs whose year and title agree, compared field by field (publisher, place, translator, extent) with the wiki publication of that year or the flat record | agreement of the two extractions per field and volume, not correctness against the book; it carries for Addendum II, and it found that edition lines under a main-volume work heading ("Bertelsmann: 383p. Gütersloh, 1952") yielded the imprint as title; p03 now reads publisher, place and year from such a line and takes the title from the work heading as an inherited value, skipping section, language, cross-reference and address-list headings |
| `p09 human sample` | concordance claims and records to a frozen blind sample, stratified by volume and by what the concordance proposed (field match, title-year block only, no candidate) | the sheet for the human check of step 7, with the key kept apart and a refusal to redraw |

The language of an object comes from the language headings within its current work or section only (fixed 2026-10-23). Before, the last language heading in the context also reached across a following work heading, so an edition line under a German work heading read the language of the preceding translation group (main volume G 67 read Swedish), and headings in capitals with a hyphen (SERBO-CROATIAN) were not recognised. Form headings inside a language group (INDIVIDUAL STORIES, SELECTED WORKS), cross-references set as headings and address lists do not end the group. No existing language value changed; wrongly inherited ones became gaps and unrecognised ones became values.

`p01` exists as `pipeline/print_volumes/p01_extract.py` and runs in the optional uv group `print` (`python -m uv run --group print python pipeline/print_volumes/p01_extract.py`). Its lines and all reports go to `data/print/derived/`, which stays local with the PDFs. The section map with page ranges, hash prefixes and the compiler's contents ranges is `pipeline/print_volumes/sections.json`. `p01` uses `pdfplumber` under an MIT licence. PyMuPDF would be faster but is licensed under the AGPL, which does not fit an MIT repository. Docling is a candidate for the reading view only, because it drops the x-positions and partly the font runs that mark boundaries and can change its output with the version of its layout models. A comparison on the same pages decides whether it enters `p02`.

Segmentation stays lossless whatever decides the boundaries. Every line belongs to exactly one unit or is marked as a running head, heading or other non-entry, and the units reproduce the source text. A rule proposes each boundary, and number sequence, position, font, page breaks, headings and resolvable addresses check one another. Where they disagree, the case goes to a residue that review or an LLM decides, recorded as a separate layer in the manner of the `proposed`, `confirmed` and `contested` states of the reconciliation. Each file gets its own rule set, because the three files differ in layout. The tail of Addendum II and the indexes are parsed separately as resolution tables or checks, never as entries.

After segmentation follow a concordance of print and wiki at entry level, first through the print addresses the wiki cites and then through title and year as candidates, and a report on what exists only in print, only in the wiki or in both, and where the versions differ. That report answers the question this strand starts from.

## Open questions

- The missing abbreviations, the broken Index A and the question which state of the main volume the file represents cannot be settled from the files, because the project has no access to a printed copy. The open-access edition of the first bibliography of 1965 may share part of the abbreviation system.
- How the post-1991 insertions in the main volume relate to Addendum I and to the wiki.
- What the starred references (`G 379*`) mean.
- Why section D of the main volume ends at 223 while the transcribed contents of 1991 give 227. An erratum of Addendum I corrects `D 224`, so the edition the errata address had entries beyond 223, and the file lacks them.
- Whether the unnumbered units of the main volume, such as collection headers and commentary paragraphs in E, become entities of their own or attach to the following entries.

## Decisions outside this strand

Admitting the print as a second documented source changes the data integrity rule of the repository, which so far admits bibliographic values only from the MediaWiki source. That decision belongs to the operator and is recorded in [Production readiness](production-readiness.md) once taken. Publishing structured data derived from the volumes raises the same rights question as publishing the PDFs, since the compiler's annotations and the compilation as a whole may be protected even where single bibliographic facts are not. The model that relates print and wiki without merging them, and the plan toward a merged Klawiter bibliography in Stefan Zweig Digital, are recorded in [Merged bibliography](print-wiki-merge.md).
