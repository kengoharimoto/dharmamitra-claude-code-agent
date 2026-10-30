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

