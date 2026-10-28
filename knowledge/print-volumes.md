---
title: "Klawiter print volumes: structure, conventions and reference system"
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: maintained
language: en
created: 2026-10-23
updated: 2026-10-24
related: [print-pipeline, data, about, status]
---

# Klawiter print volumes: structure, conventions and reference system

Randolph J. Klawiter compiled the Stefan Zweig bibliography twice, as printed volumes and as the MediaWiki that the production run rescues. Which statements exist only in print, only in the wiki or in both is not known. This document records how the three PDF files of the print volumes are built, which conventions their entries follow, how the compiler's reference system works and what a reader of the files has to expect. How the print strand turns the files into records and claims, how it is measured and how it is rebuilt is recorded in [Print pipeline](print-pipeline.md), and the model relating print and wiki in [Merged bibliography](print-wiki-merge.md).

The structural statements below come from three surveys on 2026-10-23, one per file, which extracted every line with coordinates and font runs through `pdfplumber`. A second round of agents checked each chapter schema independently against the PDFs, and the main agent spot-checked central claims of both rounds. The notes are paraphrased with their PDF pages, because the print text stays out of versioned files.

## The three files

| File | Volume | Pages | What the file is |
|---|---|---|---|
| `I Bibliography.pdf` | Stefan Zweig. An International Bibliography, Ariadne Press, 1991 | 971 | revised production file of the main volume, without front matter, with later insertions |
| `II Addendum I.pdf` | Addendum I, Ariadne Press, 1999 | 481 | complete volume with title, preface, contents, errata, abbreviations and indexes |
| `III Addendum II.pdf` | Addendum II | 1425 | the compiler's working file, without front matter, ending in a compiled tail and a letter |

The files come from the repository `chpollin/SZD`, folder `klawiter/`, commit `58234e73`, and lie in `data/print/`. Their SHA-256 values begin `9556c474…` (main volume), `d4b36ed9…` (Addendum I) and `a3de9c35…` (Addendum II) and match the SZD copies. `pipeline/print_volumes/sections.json` carries these prefixes, and the extraction refuses a file that does not match.

None of the files is a clean copy of a printed book. The main volume starts directly with the divider of section A. The printed book has xvii pages of front matter and 934 pages of text according to the catalogue of the Deutsches Literaturarchiv Marbach, and the errata of Addendum I cite those front pages ("Page xvi Add: GM = …"), so contents, introduction and abbreviation list of 1991 are missing from the file. The publisher describes the book as "17 divisions covering all of the works by and about Zweig in 57 languages", which matches sections A to Q of the file. The file also carries insertions dated up to 2001, in C 3, C 6 (a 1993 edition and a 1996 auction note), C 12, C 21 and F 50. An erratum of Addendum I is pasted into F 110 word for word, several errata are applied and others are not, and the indexes were not revised (Index C ends with 1990). The insertions follow Addendum I and in a few cases go beyond it toward Addendum II. The file is therefore a revised working state after 2001, not the 1991 print. The project has no access to a printed copy. Addendum II has no title, contents or preface. Its last pages hold a list of informants and a letter of 17 August 2009 in which the compiler says that he is preparing a second addendum to the bibliography of 1991 and its first addendum of 1999. Addendum II was never published, so the working file is its only form.

The files stay out of version control (`.gitignore`), because the volumes are presumably protected works of the compiler and the files together amount to about 155 MB, with Addendum II close to the 100 MB per-file limit of GitHub. A working copy is restored from the SZD repository and checked against the hashes above.

## Technical properties

All three files carry a born-digital text layer set in Times New Roman 12 pt, and none contains raster images, so neither OCR nor HTR is required. None is a tagged PDF, none has bookmarks, and none carries internal link annotations. Addendum II contains 15 external URLs that the producing software linked automatically from entry text. Every heading, entry boundary and reference therefore exists only as typography, position on the page and textual convention.

Font size never marks a level. Hierarchy is carried by bold, italic, capitals, the x-position of a line and vertical gaps. The files were produced in WordPerfect, and characters set in its substitute fonts (WP-MultinationalA, WP-MathA, WP-BoxDrawing and others) extract wrongly. Slavic and other diacritics appear as U+FFFF, as `\x00`, as wrong ASCII stand-ins (`ć` as `æ`, `č` as `è`, `š` as `#` in the Addendum I indexes) or as box-drawing characters. This affects field values rather than entry boundaries, and part of it cannot be repaired from the PDF at all.

`pdftotext -layout` is unsuitable as the parsing base. It shifts continuation lines to column 0 after a page break, desynchronises number columns and two-column tables, and places some entry numbers beside the wrong line. Coordinate extraction keeps all of these intact.

## What the volumes say about themselves

The compiler explains his conventions only in scattered notes. Addendum I is the one volume whose front matter survives, and its notes also describe the main volume.

- The preface of Addendum I (PDF p. 2) says that both volumes keep names and titles in the original language and give all explanatory data in English, that a periodical citation runs volume, issue, date and pages, that a newspaper citation usually gives only the date, and that cross-references are added where the compiler found them pertinent.
- The note on its abbreviations page (PDF p. 12) fixes the periodical format as volume and issue in Arabic numbers, then the date as day, month and year, then the pages. It also explains the section codes, where the first letter names the section of the 1991 bibliography and the suffix `A1` the addendum.
- The headnote of section AA2 (PDF p. 1) repeats the language rule and makes the edition data of Zweig's own volumes an exception, for which the German designations for thousand, copies and printing are kept.
- The preamble of section H in the main volume (PDF p. 290) orders the essays by subject rather than by title, so that essays on one person stand under that person's name, files the main entry of a book review under the author of the reviewed book, and falls back to the essay title when the subject is no person.

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
| IA1 Translations | 125 | Index C Sources (C1, C2) | 444–457 |
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

Addendum II is organised differently in its works sections. FA2, GA2, HA2 and DA2 each split into volume entries and work-centred entries for individual stories, essays, poems or excerpts. A work-centred entry gives the first periodical printing and then a numbered list of every reprint in a collection, each reprint cited by section code, title, year and contents number. The entry for the novella Der Amokläufer in FA2 is an example, with its first printing in a Viennese daily of 1922 followed by a numbered list of more than twenty reprints.

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
| `G 379*` | starred reference, most likely an excerpt (see below) |

No file defines the star. Starred addresses occur only in the main volume, where some page numbers carry the star as well ("p. 16*"). Addendum I restates one starred list with the excerpt abbreviation in place of the star. The poem list of B 1 in the main volume (PDF p. 21) returns in BA1 1 (Addendum I, PDF p. 19) with `[EXC]` after the one poem the main volume stars. The other cases fit the same reading of a work present only in part, since whole books are starred inside small selections and letters are starred only in printed sources. The star thus marks an excerpt in that list, and reading every star as an excerpt is an inference from it (Open questions).

The letter I is both the section of the translations and, in trade citations, the numeral of the main volume. An address in section I stands without a comma (`I 83`, PDF p. 409, cited for instance from J 68 on p. 430 and from M 89 on p. 723). Trade citations of the second Klawiter bibliography put "I," before a complete address ("Klawiter² I, F 46", [About](about.md), How the bibliography is cited), so the "I," there cannot be a section address. That reading rests on the trade citations the literature sweep recorded, since the volumes themselves never cite in that form.

Not every "See" is a cross-reference. In Addendum I about 160 of them introduce a source citation, such as an auction catalogue or a newspaper. The references also carry typing errors ("H 307, 365365", "[RSJ]"), so their parsing has to tolerate noise.

Because the notation is formal, a parser can resolve each address to its target. A reference to an address that does not exist signals either a segmentation error or an error in the print. The address probe of 2026-10-23 ([Print pipeline](print-pipeline.md), Probes) resolves almost every internal reference of the main volume and of Addendum I. The residue consists mostly of tokens that only look like addresses, such as page numbers of the Börsenblatt supplement "Aus dem Antiquariat" (`A437`), postal codes, years after a letter ("A 1988 film", "Teilband I 1933") and catalogue numbers of a Chinese series (`[B 21]`). A list such as "Reprinted A 144, 559-573" is ambiguous, because the numbers after the comma may be pages or further addresses. The compiler's explicit correction and continuation markers are rare in the sections; corrections to the main volume stand mainly in the errata pages of Addendum I.

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
| Informant sigla, main volume | Index A of the main volume (headings of the form "[= X]") and the Addendum I list | none, the other bracketed capitals there are supplied parts of names |
| Informant sigla, Addendum I | own list | used but not listed: `AMC` (PDF p. 357), `BVC` (p. 22), `KZ` (p. 298), `MH` (p. 148), `MML` (p. 285), `OM` (p. 283), `VN` (p. 80), and `RSJ` (p. 295) as a typing error for `RJS`. The listed archive siglum `SZAL` occurs only outside brackets, as a repository |
| Informant sigla, Addendum II | own list | used but not listed: `PF`, the most frequent, and `BR`, `DAP`, `EM`, `IKP` and `PS`, which the Addendum I list resolves, and `AA` (PDF p. 1387), `GK` (p. 510), `JJ` (p. 543), `JP` (p. 1250), `LNT` (p. 497), `MFG` (p. 1361), `RV` (p. 1275), `SN` (p. 269) and `UEB` (p. 289), which no list resolves. Several listed sigla are unused, and `[FIE]` (p. 547) is the abbreviation |
| Periodical sigla, main volume | Index E | three single-use near-variants (Open questions) |
| Repository sigla, letters | table in section K of the main volume | none observed |
| Source abbreviations `Zh.`, `Bild`, `Ol.` | `Zh.` is L 1757, `Bild` is L 571, `Ol.` an Index A heading of the main volume | none |
| Section codes | Addendum I, PDF p. 12 | Addendum II undocumented, read by analogy |

The residue per volume comes from the informant reader of `p03` over all entry records, each siglum checked in its line on 2026-10-24. The informant lists name private persons and institutions who supplied information. They stay in the source files and in derived research data. This document does not reproduce them.

## Hazards by file

### Main volume

- Entry numbers sometimes extract as two tokens ("5 14" on PDF p. 217).
- Index A (PDF pp. 753–916) is broken in the PDF itself. Where a reference string overran its column, the rest is drawn one character per line in a vertical strip at the column's right edge, beside the following entries. The glyphs survive in reading order, so the apparatus reader joins each strip to the entry open where it begins ([Print pipeline](print-pipeline.md), Structured objects). That attachment is a rule; whether it matches the printed book cannot be checked without a printed copy, although nearly every joined address resolves to an existing entry.
- The two columns of Index A and Index B share baselines, so a text line joins both columns; `p01` opens a run at every gap wider than a column gutter, and the apparatus reader splits lines there. Continuation lines of Index A stand at the column margin as often as indented.
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
- The indexes are set in two columns at 10 pt, so the size rule that marks page furniture in the entries does not apply to them. Their entries give a term before a colon ("Title [D 1]: DA1 2"), and titles and story lists wrap onto further lines that begin with a capital.

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
| Numbered entries | some six thousand | some two thousand | a few hundred running numbers in AA2, DA2 and the symposia list |
| Unnumbered units | several hundred `****` lines | several hundred `*` entries | several thousand blocks, entry type set by font and layout |
| Numbering gaps | a few, in G and L | a few | not applicable |
| Duplicate numbers | C 3 and F 50 | none | one run in DA2 (PDF p. 229) |

The survey and the address census of `probe_addresses.py` ([Print pipeline](print-pipeline.md), Probes) count the numbered entries of Addendum I by different methods, the survey by reading the files and the census by a chain of rising numbers, and their counts differ by one entry. The census in `reports/probe_addresses.json` is the source of the current counts.

The highest number of every section of the main volume file agrees with the contents of 1991 as the wiki transcribes them (Print and wiki), except in D and J. J runs to 79 against 75. The unrevised indexes cite J 76 to 79 with years up to 1989, so these entries stood in the 1991 print, and the transcribed contents, or the contents of 1991 themselves, leave out the end of J. D ends at 223 against 227, and its four last entries of 1991 stand in the revised file under other numbers. The indexes of the main volume and Addendum I still cite D 224 to D 227, and the errata of Addendum I correct D 224 by its printed page (PDF p. 6). The index terms of D 224 (a dedicatee, an auction house and the years 1917 and 1989, Index A PDF pp. 837 and 887, Index C pp. 920 and 924) are those of D 88a, the only suffixed number of the main volume (PDF p. 47). D 225 shares its index terms with D 98 (Index A pp. 756, 849 and 866, Index C p. 921, the entry on p. 48), and Addendum I cites the two together (p. 33). Index A cites D 226 together with D 154 (pp. 853 and 909), as Addendum I does (p. 34 and its Index A, p. 423), and D 227 together with D 159 (p. 851). D 154 and D 159 stand on PDF pp. 55 and 57. This suggests that the revision renumbered D 224 as D 88a and merged D 225 to D 227 into the entries they are cited with. The co-citations carry that reading, since the wording of 1991 is not available.

## Open questions

- Whether the joins of the vertical strips of Index A match the printed book, the exact wording of D 224 to 227 in 1991 and whether they stood under an addendum heading. These need a printed copy.
- Three periodical sigla of the main volume remain unresolved by Index E. Every other siglum the reader takes from the entries resolves, exactly, through a substitute-font defect or a column break in the index head, or as a near-variant whose citing address the index lists under the variant head. The few reader hits that name a publisher or a broadcaster are no periodicals. The three are each used once and are near-variants of an index head whose address list does not name the citing entry, `VESIL` in K 467 (PDF p. 486) beside `VESTIL` (Index E p. 967), `PHBLH` in L 568 (p. 569) beside `PHLBH` (p. 957), and `SKABS` in L 1165 (p. 624) beside `SKAKBS` (p. 963). The near heads are the likely readings, and confirming them needs a further witness. The open-access bibliography of 1965 (Carolina Digital Repository, DOI 10.17615/1m9z-gc38) uses a different and shorter siglum system and resolves none of them.
- Whether every star marks an excerpt (Reference system). The compiler's restatement shows it for one list, and the other cases are consistent with a work present only in part, an excerpt, a partial reprint or a quotation.
- Whether the unnumbered units of the main volume, such as collection headers and commentary paragraphs in E, become entities of their own or attach to the following entries.
