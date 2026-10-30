# Tibetan AHS (D4310) × Rgyud bzhi census — data and scripts

Inputs (not copied here):
- D4310 / D4311 page JSON from DharmaNexus `/text-view/text-parallels/` (downloaded with a paced, resumable fetcher).
- Rgyud bzhi e-texts: MonlamAI BO4623 (Rtsa rgyud, first part), BO2889 (Bshad), BO5092 (Man ngag ch. 1–27), BO5093 (Phyi),
  under /mnt2/code/mitra-multilingual-matching/english/repos/.
- Requires `pyewts`; the scripts look for it in a `py/` dir next to their parent `bin/` dir (pip install --target).

Usage:
    rgyud_census.py PAGES_DIR RGYUD_REPOS_DIR census_final.json 6
    rgyud_fuzzy.py  PAGES_DIR RGYUD_REPOS_DIR fuzzy_final_0.5.json 0.5
    rendering_test.py pairs_4310_4311.json RGYUD_REPOS_DIR rendering_pairs.json 0
(pairs from: nexus.sh table BO_T13_D4310 --include-files BO_T13_D4311,BO_T13_D4311-2 --par-length 20 --all)

See §6.2–6.3 of ../../tibetan-astangahrdaya-and-commentaries.md for the results and their caveats.
