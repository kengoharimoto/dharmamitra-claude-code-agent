# Aṣṭāṅgahṛdaya commentaries — OCR

Goal: clean e-texts of the surviving Sanskrit commentaries on Vāgbhaṭa's Aṣṭāṅgahṛdayasaṃhitā (AHS):

| Commentary | Author | Extent | Source edition |
|---|---|---|---|
| Padārthacandrikā | Candranandana | Sūtrasthāna only (the rest survives only in Tibetan, Tōh. 4312) | `t1928` |
| Sarvāṅgasundarā | Aruṇadatta | complete | `parad` (and Sū. also in `t1928`) |
| Āyurvedarasāyana | Hemādri | partial (Sū., Ni. part, Ka. …) | `parad` (and Sū. also in `t1928`) |

Sources:
- `t1928`: *Aṣṭāṅgahṛdaya … with the commentaries of Aruṇadatta (Sarvāṅgasundarā), Candranandana
  (Padārthacandrikā) and Hemādri*, Sūtrasthāna, ed. Rām Prasād Śarmā, 1928. archive.org item
  `ashtangahridayavagbhattacommentaryofarunadattapadarthachandrikachandranandatikah_167_i`
  → `src/ahs_tika1928.pdf` (562 pp., 300 dpi bitonal). Sigla: स० Aruṇadatta, प० Candranandana, हे० Hemādri.
- `parad`: Nirṇaya Sāgar edition revised by Hari Śāstrī Parāḍkar (Sarvāṅgasundarā + Āyurvedarasāyana),
  `/qnap/kengo/dox/Books_and_Articles_on_iCloud/Ashtanga.Hridaya.of.Vagbhata.pdf` (1,143 pp., 300 dpi
  bitonal). Sigla: स० Aruṇadatta, आ० र० Hemādri. Footnotes (variant readings, MS sigla क ख …) at page foot.

Layout of both: two columns; mūla in large bold type, each commentary in small type after the
mūla unit, opened by its siglum.

Scan defects (t1928): leaves are missing from the archive.org scan (printed pp. 52–53, 80–81, 160–161,
… — full list in `check/t1928_report.json`, detected from the running-head page numbers). A second
archive.org upload (`astangahrdayasutrasthana3commentaries3`) is the same scan (562 pp., identical
page images), so it cannot fill the gaps.

## Engine
Surya OCR 2 via vLLM on GPU 1, port 8092 (`logs/surya-server.log`), following the A/B result of
`../ocr-cakrapani` (Surya clearly better than Chandra on NSP Devanagari). Spot check here: Surya reads
the 1928 commentary cleanly where the archive.org OCR layer is badly garbled.

## Pipeline
1. `run_surya.sh BOOK FIRST LAST` → `surya_out/BOOK/chunk_*/…/results.json` (full-page OCR, resumable).
2. `assemble.py BOOK` → `etext/`: separates mūla, the commentaries (by siglum), lead-ins and footnotes.
   Mūla is located by fuzzy-matching every verse of the Das & Emmerick AHS e-text
   (`E-texts/1_sanskr/6_sastra/7_ayur/vagbhata_astangahrdaya.txt`) against the OCR stream, which also
   anchors each commentary passage to its verse (e.g. `[Sū.3.43]`). Surya's bold tagging and line
   breaks are too unreliable here for type-size based separation.
3. Checks: share of D&E verses located; letter agreement on located mūla (an OCR-quality estimate);
   mūla shingles left inside commentary files.

## Progress log
- 2026-10-30 16:58: project set up, scan downloaded, Surya server started on GPU 1.
- 17:00: full-page OCR launched (t1928, then parad).
- 17:05: assemble.py: mūla located per half-verse (t1928 prints the mūla an ardha at a time); missing
  leaves detected from running-head numbering.
- 17:15: user request: align every Tibetan commentary (D4311, D4312) against every Sanskrit
  commentary, regardless of titles.
- 17:14: t1928 OCR done (562 pp.). assemble.py t1928: 1,515/1,593 regular Sū. verses located (rest:
  3 missing leaves + edition differences), mūla letter agreement with D&E 95.0 %; sigla variants
  (म/ह/ष, स्/सू after a verse number) and the editor's "( n )" notes handled; long unlabelled
  passages kept apart as `unassigned` (editor's ṭippaṇī, lost sigla; ~4 % of commentary text);
  exact page markers. Commentary text: Candranandana 501k, Aruṇadatta 502k, Hemādri 457k chars.
- 17:20: clean Padārthacandrikā vs Tibetan D4312 (Sū.): median cos of matched pairs 0.865 (OCR layer
  of archive.org: 0.827; wrong pairs 0.74), locally confirmed 60 % (was 46 %), chapter agreement 97 %.
- 18:09: parad OCR done (1,143 pp.). Front matter of ~177 pp. (preface quoting Sū.1.1, indexes):
  matcher now anchors only on occurrences confirmed by the next verses, and re-anchors after a run of
  misses. parad: 7,250/7,441 regular verses located, mūla agreement 95.5 %; one missing leaf (printed
  pp. 658–659). Sigla: आ० २० (= आ० र०); प० चं० = Padārthacandrikā passages printed by Parāḍkar outside
  the Sūtrasthāna (e.g. U.21; 21 passages); Aruṇadatta printed without siglum where he is the only
  commentator (most of Śārīrasthāna) → assigned to him (`nosig`); verse quotations inside an open
  commentary are given back to it. Line-end breaks "X- Y" (Surya's form) joined.
- 18:20: e-texts installed in E-texts/1_sanskr/6_sastra/7_ayur (IAST + _deva; log
  catalog/move_log_20261030_182205_ahs_commentaries_ocr.tsv; a first install minutes earlier, before the
  hyphen fix, moved to _trash, log catalog/trash_log_*_ahs_commentaries_superseded.tsv).
- Correction: the 1928 edition *does* print Candranandana's introductory verses (p. 26, no siglum);
  the archive.org OCR layer had hidden them. They match the Tibetan D4312:1b verse by verse.
- Tibetan anchoring: D4312 by fuzzy lemma matching against D4310 (`tib_d4312.py`: 4,705/5,559 blocks,
  median score 98.6, 10 backward steps in 5,505); D4311 by its own numbered chapter colophons
  (sub-section colophons in Sū.5–6 are unnumbered) + within-chapter Viterbi (`tib_d4311.py`: all 120
  chapters, mean cos 0.784).
- 18:15: cross-alignment (`xprep.py`, `xalign.py`) launched: every Tibetan commentary (D4311, D4312)
  against every Sanskrit one (Aruṇadatta, Hemādri, Candranandana; 1928 witnesses too). Chunks built from
  the e-texts before the hyphen fix (negligible for the embeddings).

- 18:45: cross-alignment results (check/xalign.json; summary in the dharmamitra repo,
  output/reports/data/tibetan-ahs-commentary-crossalign/). D4312 matches Candranandana best (Sū: 24.4 %
  clear matches, 3.0 % ≥ 0.90; Parāḍkar प० चं० excerpts 52.6 %); the Vaiḍūryakabhāṣya (D4311) matches no
  surviving Sanskrit commentary (≥ 0.90: 0.0–0.1 %). D4312↔Aruṇadatta similarity (16–22 %) is verse
  paraphrase, not copying: the matching Aruṇadatta passages contain fewer sentences shared with
  Candranandana's Sanskrit (4.8 %) than the rest (17.4 %). Surya server stopped (GPU 1 freed).

## 2026-10-31 — text reuse among the Sanskrit commentaries
Scripts: `reuse.py` (exact 24-letter shingle runs; lower bound, OCR-sensitive), `reuse2.py` (sentence-level
fuzzy, partial_ratio ≥ 85 against the other commentary on the same verse ±3; null = other chapters = 0 %;
control = same commentary in the two editions ≈ 68–74 %). Outputs: check/reuse.json, reuse2.json,
reuse_perchapter.json, reuse_sources.json.
- Aruṇadatta ← Candranandana (Sū): 11.3 % of sentences (6.1 % verbatim); same in Parāḍkar's independent
  Aruṇadatta (10.6 %). Concentrated: Sū.1 ≈ 41 %, Sū.6 33–40 %, Sū.7 32 % (72 % in the 1928 ed.), Sū.30
  12–14 %; elsewhere 0–5 %. Paraphrase baseline (Hemādri ← Candranandana) 2.4 %.
- Hemādri shares ≤ 2.4 % with either; outside Sū (Parāḍkar) Aruṇadatta↔Hemādri 0.3–0.4 %.
- Parāḍkar's प० चं० excerpts share nothing with Aruṇadatta (that is why Parāḍkar printed them).
- Quotations (exact runs, lower bound): Hemādri 11–13 % Aṣṭāṅgasaṃgraha; Aruṇadatta 1.8–3.1 %; Candranandana 1.4 %.

## 2026-10-31 — why Parāḍkar's Hemādri shares more with Candranandana (5.5 % vs 2.4 %)
Cause: misfiling in the t1928 split, not a difference between the editions. Two mechanisms:
1. Footnote cut was page-wide: on p. 33 the editor's notes start mid-way down the right column, and
   everything below that height in the left column (Hemādri's note on Sū.1.6 with its siglum) was dropped
   as a note; its continuation at the top of the right column then attached to the open Candranandana
   passage. Fixed in assemble.py for t1928 (cut only below a note-seed in the same column; parad keeps
   the page-wide rule, its variant notes span both columns). Recovers ~2.4k chars; t1928 etext/
   regenerated (old outputs in check/before_colfix/). Library copies NOT yet re-installed.
2. Misread/lost sigla (e.g. Sū.1.24, Sū.5.43 passages carrying the wrong siglum; a 15k-char
   "Hemādri" segment at Sū.7.26). Suspects (sentence in the other commentator's Parāḍkar text ≥ 90,
   not in its own, not in the other's 1928 stream): check/misfile_suspects_t1928.json — 2.4–6.3 % per
   stream, upper bound (includes verses both commentators quote).
With the suspects removed (check/robust.py): Hemādri(Par.) ← Candranandana 5.5 → 2.9 % (1928 Hemādri
1.9–2.4 %). Aruṇadatta(Par.) ← Candranandana: Sū.1 41 → 26 %, Sū.6 33 → 28 %, Sū.7 32 → 26 %,
Sū.30 12 %, other chapters 2.0 → 1.7 % — the block-copying finding stands; Sū.1 is 26–41 %.
- 2026-10-31 11:54: t1928 e-texts re-installed after the column-aware note fix (old copies → _trash, catalog/trash_log_*_ahs_commentaries_t1928_colfix.tsv; new: catalog/move_log_20261031_115437_ahs_commentaries_ocr.tsv). §12 figures re-run: unchanged to ±0.1 %.

## 2026-10-31 — page-image check of the misfiling suspects; siglum recognition fixed
- `siglcheck/clusters.py`: the 748 locatable suspect sentences → 216 clusters; `siglcheck/crops.py` /
  `crops2.py`: page-image crops (column around the passage; second pass: whole block + preceding block).
  Read by four + two subagents, spot-checked by hand. Verdicts: `siglcheck/verdicts_final.json`
  — 140 correct (mostly Candranandana text repeated by Aruṇadatta, or shared quotations), 51 misfiled
  (46 siglum seen, 5 inferred from paragraph order where the scan edge cuts the siglum), 9 not commentary,
  5 printed without siglum, 11 unclear.
- Causes found and fixed in assemble.py (both books):
  1. a siglum at the top of a page follows the page marker , which the siglum regex did not accept
     as a left boundary → the whole paragraph stayed with the preceding commentator (t1928: ~34k chars
     recovered from "unassigned"; parad: 41k chars of Hemādri had been filed under Aruṇadatta);
  2. OCR forms हृ०/ह्० (हे०), हे-- without ०, स० without dash (accepted only after a verse number, at a page
     top or region start), and प० च० for प० चं० (parad: Candranandana excerpts 21 → 42 passages, U.21–22);
  3. "प्र. टी." (t1928 Sū.13.15, two glosses beside the commentaries) kept apart as unassigned;
  4. three remaining confirmed cases as manual overrides: check/sigla_overrides.json.
  Of the 51 misfiled: 37 now correct, 3 duplicated in both commentaries (copying/quotation; no change),
  3 by override, 2 (ids 15, 137) turned out to be copied text present in both; 5 inferred left unchanged;
  1 (id 139) was a non-case. All 140 "correct" passages are still in place. Mūla figures unchanged.
- Re-detected suspects: 59k → 28k letters (remaining mostly copying/quotations, per the image check).
- New observation: Aruṇadatta Sū.1.14 (p. 42, स० seen) contains a long sāmānya/viśeṣa discussion shared
  with Cakrapāṇi's Āyurvedadīpikā (check/cakrapani_overlap.py) — 1.4 % of Aruṇadatta's Sū text.
- Library re-installed (all 12 files; old → _trash, catalog/trash_log_*_ahs_commentaries_sigla_fix.tsv;
  new: catalog/move_log_20261031_122403_ahs_commentaries_ocr.tsv). Cross-alignment re-run (xalign).

## 2026-10-31 — third pass: unclear and inferred cases
- `siglcheck/walkback.py`: for each of the 16 unclear/inferred runs, crops of its block and the blocks
  before it (across columns/pages) back to the paragraph's siglum; plus Parāḍkar as independent evidence
  (its own siglum split, different page breaks). Viewed by hand. Results in verdicts_final.json (pass3).
  Correct: 3, 14, 19, 162 (and 115–117, 172 already right after pass 2). Corrected: 1 → Aruṇadatta
  (OCR "६॥ स्व०—"), 32 (Sū.1.43: 2nd note → Candranandana, 3rd → Hemādri), 51/52 → Hemādri (3rd note
  on Sū.5.4; = Parāḍkar), 53 → Aruṇadatta (1st note on Sū.5.5; = Parāḍkar's Aruṇadatta verbatim),
  122/123 → Candranandana (2nd of 3 notes on Sū.7.31). 109 unresolved (Saṃgraha quotation in several).
  Pass-2 verdict for 121 corrected (agent note said स० paragraph). 15, 137: present in both (copying).
- Further assemble.py fixes found on the way:
  1. verse matches that ran past the verse number into the next siglum ("… ॥ २७ ॥ स०--न") are trimmed
     at the verse number (t1928: 41, parad: 174 such sigla; parad: 11k chars of Aruṇadatta had been
     attached to Hemādri via the quotation-repair step);
  2. SIG_WEAK: स्व० and a verse number without its opening ॥ ("६॥");
  3. t1928 editor's notes numbered without parentheses ("१ अत्र … पाठान्तरम्", 60 blocks) are now note
     seeds (notes file 41k → 93k bytes; checked: no commentary siglum among the moved text except an
     editor's "१ स०-- … प्र. दी." note);
  4. overrides gain an optional "from" (only a segment filed under that commentator).
- Verification: all 198 decided runs (147 correct + 51 misfiled) are now in the commentator the page
  shows. Suspect letters: 28k → 26k. Library re-installed (catalog/move_log_20261031_124203_…;
  old copies → _trash, trash_log_*_ahs_commentaries_pass3.tsv). Cross-alignment re-run (logs/xalign_rerun2.log).
