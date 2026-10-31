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

Run with the system python: `python3 -P <script>`. `reuse_ch.py`, `reuse_dist.py` and `quotes.py` load
their definitions from `/mnt2/kengo/ocr-ahs-tika1928/reuse2.py`.
