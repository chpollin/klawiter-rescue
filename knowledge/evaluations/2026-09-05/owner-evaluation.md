# Owner evaluation — 20–30 minutes

Please judge the bibliographic interpretation and the usefulness of the interface. Parser implementation and test mechanics are being reviewed independently by agents. These are proposed acceptance cases, not approved corrections.

The existing project decision already requires multi-edition pages to be represented as works and editions. No new approval of that general principle is needed here. The concrete questions concern publication boundaries, roles and presentation.

Reply in the chat with `case number: accept / change / unclear`, plus a short correction where needed. “Unclear from this source” is a valid outcome; it should become an explicit review case.

The [complete source texts](source-only.json) and [consolidated review](../../independent-evaluation-2026-09-05.md) are available beside this worksheet. Cases 1–4 evaluate proposed interpretation and presentation; case 5 evaluates the current frontend.

## 1. Two editions on one source page — 1800

Source title: **Romanŭt na edin zhivot. Balzak**.

| Publication | Publisher | Place | Translator | Source extent |
|---|---|---|---|---|
| 1947, first edition | Pechat Far | Sofija | Dimitŭr Stoevski | 500p. |
| 1960, second revised edition | Narodna Kultura | Sofija | Dimitŭr Stoevski | 383/(1)p. |

Proposed display: two individually citable editions under the preserved source page, with fields and evidence attached to their own edition. A search result must make the selected edition clear.

Evaluate: Does this capture the bibliographic distinction correctly, and what information would you need to cite either edition confidently?

## 2. Translators of contributions — 1891

Source title: **Mariia Stiuart * Kazanova**, Kavkazskiĭ Krai, Stavropol’, 1993.

The source attributes Maria Stuart to **R. Gal’perina**, its verses to **V. Levik**, and Casanova to **P. S. Bernshteĭn**. **N. Vysotskaia** is the editor. The volume states `444/(3)p.`, while the contents end at page 445.

Proposed display: preserve all three translation roles and their contribution scope; keep the editor separate. Show the original extent notation and flag the apparent pagination inconsistency for review. A blank scalar translator must not imply that no translators are documented.

Evaluate: Is this the right level of detail for your research use, including how the source inconsistency is displayed?

## 3. German book and Arabic article — 4445

Source title: **Al-Bāḥ, Muḥammad / El-bah, Mohammed**.

- German section: *Frauen- und Männerbilder in den Novellen von Stefan Zweig*, Hochschulverl., Freiburg im Breisgau, 2000, 168p.; based on a 1999 thesis.
- Arabic section: a 2015 journal article in *Al-Balāghah waʾl-naqd al-ʿarabī*, Rabat, pp. 71–79.
- The page categories list Arabic and German.

Proposed display: two publications, each with its own language and citation context. Page categories remain discoverable. The source alone does not establish that the Arabic article is a translation or edition of the German book.

Evaluate: Should these be linked only through their source page/author until their work relationship has been reviewed, and is the distinction understandable in the interface?

## 4. Two publication places and a name variant — 4209

Source title: **Vreemdes in 'n vreemde wêreld**, Nasionale Pers Beperk, 1947.

The imprint gives **Bloemfontein, Kaapstad (Capetown)**. The main translation statement names **Hymne Weiss**; the contents describe foreword material with the spelling **Hymme Weiss**. The language category is Afrikaans and the extent is `160p.`.

Proposed display: retain both publication places and their source wording. Show Hymne Weiss as the explicitly credited translator; retain the alternate spelling in its source context, without silently asserting an identity correction.

Evaluate: Does this preserve enough information, and should the spelling variation be prominent or available in the evidence panel?

## 5. Complete one real research task

Use the current frontend with one item you know well. Record whether you can:

1. Find the intended publication through search and a relevant language filter.
2. Determine which edition/publication each displayed field describes.
3. Inspect its source evidence and understand exactly what has been reviewed.
4. Export a citation that you would actually use.
5. Repeat the essential steps on a narrow screen or with the keyboard.

Record the entry ID, the first point of confusion or failure, and what you expected instead. Known defects may make a task fail; that is useful evidence, not a request to work around them.

## What the agents cover

Two separate reviewers examined the twenty source texts without current test expectations or failure baselines. A third reviewer checked the test gates and whether the chosen expectations encode unapproved selection rules. Their findings have been compared with the existing expectations in the consolidated review. Agreement is supporting evidence, not a substitute for scholarly adjudication.
