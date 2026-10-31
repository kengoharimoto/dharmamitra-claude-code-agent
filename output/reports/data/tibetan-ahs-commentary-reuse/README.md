# Text reuse among the Sanskrit AHS commentaries (report §12)

Data for §12 of `../../tibetan-astangahrdaya-and-commentaries.md`. Inputs are the Surya-OCR e-texts in
`/mnt2/kengo/ocr-ahs-tika1928/etext/` (`*_structure.jsonl`) and the āyurveda texts of the E-text library.

| File | Content |
|---|---|
| `reuse2.py` → `reuse2.json` | Sentence-level fuzzy reuse (partial_ratio ≥ 85 vs the other commentary on the same verse ±3); controls; longest shared sentences |
| `reuse_ch.py` → `reuse_perchapter.json` | The same, per Sūtrasthāna chapter, both editions |
| `reuse_dist.py` | Score distribution at thresholds 65–95 vs the other-chapter baseline (printed only) |
| `reuse.py` → `reuse.json` | Exact 24-letter run matching (lower bound, OCR-sensitive) |
| `quotes.py` → `reuse_sources.json` | Quotations of Caraka, Suśruta, Saṃgraha, etc. (exact runs ≥ 40 letters) |
| `misfile3.py` → `misfile_suspects_t1928.json` | Sentences of a 1928 stream that are probably another commentator's (misfiled by the OCR split) |
| `robust.py` | §12 figures with those suspects removed (printed only) |
| `assemble.py`, `install.py` | Current versions (column-aware notes for t1928; siglum fixes and overrides, 2026-10-31) |

Run with the system python: `python3 -P <script>`. `reuse_ch.py`, `reuse_dist.py`, `quotes.py`,
`misfile3.py` and `robust.py` load their definitions from `/mnt2/kengo/ocr-ahs-tika1928/reuse2.py`;
`misfile3.py` writes `misfile3.json` in the current directory, and `robust.py` reads it from there.

Page-image check of the misfiling suspects (§12): `siglcheck/` — `clusters.py` (suspects → runs),
`crops.py` / `crops2.py` (page-image crops; the PNGs themselves stay in `/mnt2/kengo/ocr-ahs-tika1928/siglcheck/`),
`clusters.json` (runs with crop paths), `verdicts_final.json` (siglum read off the page per run).
`sigla_overrides.json`: the three hand corrections applied by `assemble.py`.
`cakrapani_overlap.py`: locates Aruṇadatta passages shared with Cakrapāṇi's Āyurvedadīpikā.
