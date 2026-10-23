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

The structural statements below come from three surveys on 2026-10-23, one per file, which extracted every line with coordinates and font runs through `pdfplumber`. The main agent checked their central claims against the PDFs.

## The three files

| File | Volume | Pages | What the file is |
|---|---|---|---|
| `I Bibliography.pdf` | Stefan Zweig. An International Bibliography, Ariadne Press, 1991 | 971 | revised production file of the main volume, without front matter, with later insertions |
| `II Addendum I.pdf` | Addendum I, Ariadne Press, 1999 | 481 | complete volume with title, preface, contents, errata, abbreviations and indexes |
| `III Addendum II.pdf` | Addendum II | 1426 | the compiler's working file, without front matter, ending in a compiled tail and a letter |

The files come from the repository `chpollin/SZD`, folder `klawiter/`, commit `58234e73`, and lie in `data/print/`. Their SHA-256 values begin `9556c474…`, `a3de9c35…` and `d4b36ed9…` and match the SZD copies.

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
| M | Reviews | MA1 Reviews | none, MA2 occurs in a few references |
| N | Film Versions of Zweig's Works | NA1 Stage Productions, Movies | none |
| O | Zweig's Works Set to Music | OA1 Works Set to Music | none, poems set to music stand in DA2 |
| P | Zweig Symposia, Centennial 1981 | PA1 Symposia and Exhibitions 1992–1996 | P section and a symposia list in the tail |
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

Section titles differ between table of contents, running heads and divider pages within one volume, for instance EA1 "Dramas" and "Dramas and Scenarios". The page numbers in the contents of Addendum I drift by up to seven pages from the body, while its entry-number ranges match exactly, so entry numbers are the reliable locator. Printed page numbers and PDF page numbers diverge in every file, because blank and divider pages are missing from the PDFs. Addendum II carries no printed page numbers before its tail.

## Levels below the section

Below the section the volumes use the same kinds of units, marked differently in each file.

| Unit | Main volume | Addendum I | Addendum II |
|---|---|---|---|
| Section divider | divider page with letter and title | no body heading, only running heads and "Graphic Page (n) XA1 / TITLE" placeholder lines | bold capital line at page top |
| Sub-genre or part | Arial bold mixed case (B–E) or Times bold capitals (F, K, L, M), e.g. "Collected Poems", "INDIVIDUAL LETTERS" | bold capitals | bold capitals, e.g. "Volumes", "Individual stories", "Excerpts" |
| Language | bold capitals or Arial bold, alphabetical | bold capitals, German implicit without heading | bold capitals, about fifty languages in FA2 |
| Work heading | roman capitals in G (e.g. AMERIGO, BALZAC) with "* * * * *" separators, Arial bold in E with an unnumbered commentary paragraph | bold capitals with bracketed references in MA1 | none, work-centred entries instead |
| Preamble or note | flush paragraph headed "Secondary Literature:" or "NB:" | "NB:" paragraphs | "Nota bene", "NB:" |
| Numbered entry | number at the left margin, text with hanging indent | bold number at the left margin, hanging indent | running numbers only in AA2, DA2 and the symposia list |
| Cross-reference stub | `****` | `*` | `***` in DA2, otherwise short "See" entries |
| Sub-item | `[1]. [2].`, `Vol. n.` | `[1].`, `[a]`, `Vol. I.` | `[1].`, `[X].`, `[a]`, `Vol. n.` |

The main volume also contains collection headers in section A, an unnumbered series title with a descriptive paragraph followed by the volumes as numbered entries, and "ADDENDUM" headings near the end of sections A, C, F, G, H, J, K and L whose entries continue the section's numbering. Several sections have further levels. E groups its entries under twelve drama work headings with language headings below them, I under translated authors ("BAUDELAIRE, CHARLES: INDIVIDUAL POEMS"), K under "REPOSITORIES", "COLLECTED LETTERS" and "INDIVIDUAL LETTERS", and M under genre headings that mirror sections A to L. G uses roman inline labels such as "Excerpt" and "Individual Historical Miniature" inside its work blocks. Section K has its own table of repository sigla (PDF pp. 433–435).

The preambles headed "Secondary Literature:" in sections B to K are lists of cross-references into L and M, sorted by topic ("Zweig as dramatist see L 132, …", "Reviews M 20-31"). They form a second, topical access to the reference network. In section LA1 of Addendum I, language and genre headings are typographically identical, so only a vocabulary separates them.

Addendum II is organised differently in its works sections. FA2, GA2, HA2 and DA2 each split into volume entries and work-centred entries for individual stories, essays, poems or excerpts. A work-centred entry gives the first periodical printing and then a numbered list of every reprint in a collection, each reprint cited by section code, title, year and contents number.

> "Der Amokläufer. Eine Novelle" [1922] in *Neue Freie Presse* … Reprinted as … in [2]. AA2 1 Amok… 1950 [1], pp. (5)-(59). … [23]. LA2 Jacquot…

These lists belong to the bibliography's own record of printing history, and in practice they work as a concordance between works and collections. Earlier sampling had suggested that the volume contains separate registers by work or translator. The survey found one explicit subject register (PDF p. 617, "Autographs - Collecting and Collections, see: [1]. HA2 …") and no concordance by translator.

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
| `[See p. 934]`, `[Zh., 681]`, `See Bild, No. 87, p. 91` | page reference or reference to an external source |
| `G 379*` | starred reference, meaning not defined in any of the files |

Not every "See" is a cross-reference. In Addendum I about 160 of them introduce a source citation, such as an auction catalogue or a newspaper. The references also carry typing errors ("H 307, 365365", "[RSJ]"), so their parsing has to tolerate noise.

Because the notation is formal, a parser can resolve each address to its target. A reference to an address that does not exist signals either a segmentation error or an error in the print. The wiki cites the same addresses (`See F 455`, `HA1 152`, `LA1 229`) and carries the sigla `[PF]` and `[RJS]`, which makes the address system the primary anchor for comparing print and wiki. How completely the wiki carries print addresses has not been measured.

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
- Index A (PDF pp. 753–916) is broken in the PDF itself. Long reference strings are drawn one character per line in vertical columns, so the index cannot be recovered from this file and must come from the printed book or be rebuilt from the entries.
- Index pagination overlaps, because Index C restarts at printed page 884 inside the range Index A claims.
- The hanging indent varies between sections (108, 122, 144 and 150 pt against a margin of 72 pt), so continuation means "x greater than the margin".
- Entry numbers are mostly bold in A–H but always roman with a letter prefix in E and I–Q, so font is no reliable start criterion. Position and number sequence are.
- Revised regions carry editing debris (PDF p. 105) and two duplicate numbers, C 3 and F 50, both at post-1991 insertions.
- Flush paragraphs whose wrapped lines begin with a number look like entry starts.
- Line-end hyphens before digits are mostly ranges but sometimes split numbers ("11-/51" for L 1151).

### Addendum I

- The errata to the main volume (PDF pp. 6–11) form a two-column list addressed by page and siglum of the main volume, including renumberings ("Renumber as H 152a") and corrections of its index pages. They need their own parser.
- Some entry numbers are split across fonts or glued to the first word ("1040aPinto,").
- Overprinted háček glyphs split one line into two on a few pages.
- The indexes are set in two columns at 10 pt.

### Addendum II

- The tail after the secondary literature is a compilation. Advertisements for Zweig's works appear twice with practically identical text (PDF pp. 1388–1392 and 1408–1413), the 1981 symposia appear twice, an English list of works without section codes (pp. 1398–1408) follows another scheme, and a stray running head recurs on the last pages.
- Draft flags such as "NEED INFO" are set in bold capitals and look like headings (PDF pp. 532–536).
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

## Approach

The analysis proceeds in stages, each with an inspectable output.

| Stage | Input and output | Purpose |
|---|---|---|
| `p01 extract` | PDF to lines as JSONL, with volume, page, coordinates, font runs, text and hash | lossless deterministic base, running heads and page numbers marked rather than removed |
| `p02 view` | lines to Markdown per volume and section | reading view, derived and regenerable |
| `p03 segment` | lines to entries with section, number, line span and raw text | entry boundaries, across page breaks |
| `p04 sample` | entries to a hand-checked sample | reference set for tests, stratified by file, section and the hazards above |
| `p05 parse` | entries to fields | after the conventions are fixed |
| `p06 resolve` | addresses to target entries | reference graph and a self-check of the segmentation |

`p01` uses `pdfplumber` under an MIT licence. PyMuPDF would be faster but is licensed under the AGPL, which does not fit an MIT repository. Docling is a candidate for the reading view only, because it drops the x-positions and partly the font runs that mark boundaries and can change its output with the version of its layout models. A comparison on the same pages decides whether it enters `p02`.

Segmentation stays lossless whatever decides the boundaries. Every line belongs to exactly one unit or is marked as a running head, heading or other non-entry, and the units reproduce the source text. A rule proposes each boundary, and number sequence, position, font, page breaks, headings and resolvable addresses check one another. Where they disagree, the case goes to a residue that review or an LLM decides, recorded as a separate layer in the manner of the `proposed`, `confirmed` and `contested` states of the reconciliation. Each file gets its own rule set, because the three files differ in layout. The tail of Addendum II and the indexes are parsed separately as resolution tables or checks, never as entries.

After segmentation follow a concordance of print and wiki at entry level, first through the print addresses the wiki cites and then through title and year as candidates, and a report on what exists only in print, only in the wiki or in both, and where the versions differ. That report answers the question this strand starts from.

## Open questions

- The missing abbreviations, the broken Index A and the question which state of the main volume the file represents cannot be settled from the files, because the project has no access to a printed copy. The open-access edition of the first bibliography of 1965 may share part of the abbreviation system.
- How the post-1991 insertions in the main volume relate to Addendum I and to the wiki.
- What the starred references (`G 379*`) mean.
- Whether the unnumbered units of the main volume, such as collection headers and commentary paragraphs in E, become entities of their own or attach to the following entries.

## Decisions outside this strand

Admitting the print as a second documented source changes the data integrity rule of the repository, which so far admits bibliographic values only from the MediaWiki source. That decision belongs to the operator and is recorded in [Production readiness](production-readiness.md) once taken. Publishing structured data derived from the volumes raises the same rights question as publishing the PDFs, since the compiler's annotations and the compilation as a whole may be protected even where single bibliographic facts are not. The long-term target is a curated, merged Klawiter dataset in Stefan Zweig Digital, exported as TEI from the work/edition graph with every statement keeping its source location in wiki or print.
