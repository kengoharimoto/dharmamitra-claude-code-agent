#!/usr/bin/env python3
"""Install the AHS commentary e-texts into the E-text library (IAST + _deva), log in catalog/.
Never overwrites: refuses if a target exists.   Usage: python3 -P install.py [BOOK ...]   (default: all)"""
import datetime, json, re, sys
from pathlib import Path

P = Path("/mnt2/kengo/ocr-ahs-tika1928")
LIB = Path("/mnt2/kengo/E-texts")
D = LIB / "1_sanskr/6_sastra/7_ayur"

ED_1928 = """#   Edition: Aṣṭāṅgahṛdaya, Sūtrasthāna, with the Sarvāṅgasundarā of Aruṇadatta, the Padārthacandrikā of
#   Candranandana and the Āyurvedarasāyana of Hemādri, ed. Rām Prasād Śarmā, 1928 ("saṭippaṇaṭīkātrayasaṃvalita");
#   scan: archive.org ashtangahridayavagbhattacommentaryofarunadattapadarthachandrikachandranandatikah_167_i.
#   The scan lacks leaves (printed pp. 52–53, 80–81, 160–161; see check/t1928_report.json)."""
ED_PARAD = """#   Edition: Aṣṭāṅgahṛdaya with the Sarvāṅgasundarā of Aruṇadatta and the Āyurvedarasāyana of Hemādri,
#   ed. A. M. Kuṇṭe and K. R. Ś. Navare, revised by Hari Śāstrī Parāḍkar, Nirṇaya Sāgar Press, Bombay (1939);
#   scan: /qnap/kengo/dox/Books_and_Articles_on_iCloud/Ashtanga.Hridaya.of.Vagbhata.pdf (lacks printed pp. 658–659)."""
COMMON = """#   Source: uncorrected Surya OCR 2 (2026-10-30); pipeline, reports and the page-faithful structure file in
#   /mnt2/kengo/ocr-ahs-tika1928 (README.md).
#   Separation: the mūla was located by fuzzy-matching every verse of the Das & Emmerick e-text
#   (vagbhata_astangahrdaya.txt) in the OCR stream; commentaries were split by their sigla. Expect some
#   misfiled passages where the OCR lost or garbled a siglum.
#   Format: one passage per line, "[verse] [p. N]": verse = Das & Emmerick number of the mūla the passage
#   follows (ab/cd = half-verse), N = PDF page; ## = chapter."""

JOBS = [  # (book, who, file name, title, edition, extra note)
    ("t1928", "candranandana", "candranandana_padarthacandrika_sutrasthana_sarma1928-ed_ocr",
     "Candranandana, Padārthacandrikā (commentary on the Aṣṭāṅgahṛdaya), Sūtrasthāna — the only part surviving in Sanskrit; Tibetan: Tōh. 4312.",
     ED_1928, ""),
    ("t1928", "arunadatta", "arunadatta_sarvangasundara_sutrasthana_sarma1928-ed_ocr",
     "Aruṇadatta, Sarvāṅgasundarā (commentary on the Aṣṭāṅgahṛdaya), Sūtrasthāna, in the 1928 three-commentary edition.",
     ED_1928, "#   Complete text of this commentary: arunadatta_sarvangasundara_paradkar-ed_ocr.txt.\n"),
    ("t1928", "hemadri", "hemadri_ayurvedarasayana_sutrasthana_sarma1928-ed_ocr",
     "Hemādri, Āyurvedarasāyana (commentary on the Aṣṭāṅgahṛdaya), Sūtrasthāna, in the 1928 three-commentary edition.",
     ED_1928, ""),
    ("parad", "arunadatta", "arunadatta_sarvangasundara_paradkar-ed_ocr",
     "Aruṇadatta, Sarvāṅgasundarā (commentary on the Aṣṭāṅgahṛdaya), all six sthānas.",
     ED_PARAD, "#   Where Aruṇadatta is the only commentator (e.g. most of Śārīrasthāna) the edition prints him without a\n#   siglum; such passages are included here.\n"),
    ("parad", "hemadri", "hemadri_ayurvedarasayana_paradkar-ed_ocr",
     "Hemādri, Āyurvedarasāyana (commentary on the Aṣṭāṅgahṛdaya), as far as printed in the Parāḍkar edition.",
     ED_PARAD, ""),
    ("parad", "candranandana", "candranandana_padarthacandrika_excerpts_paradkar-ed_ocr",
     "Candranandana, Padārthacandrikā: the passages printed in the Parāḍkar edition under the siglum प० चं० (e.g. U.21), outside the Sūtrasthāna.",
     ED_PARAD, ""),
]

def body(book, who, enc):
    f = P / "etext" / f"{book}_{who}{'.iast' if enc == 'iast' else ''}.txt"
    return "\n".join(l for l in f.read_text().splitlines() if not l.startswith("% ")).lstrip("\n") + "\n"

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log = [("src", "dest", "reason")]
BOOKS = set(sys.argv[1:]) or {"t1928", "parad"}
for book, who, name, title, ed, extra in JOBS:
    if book not in BOOKS: continue
    for enc, suffix in (("iast", ""), ("deva", "_deva")):
        dest = D / f"{name}{suffix}.txt"
        if dest.exists(): raise SystemExit(f"refusing to overwrite {dest}")
        hdr = f"# {title}\n{ed}\n{COMMON}\n{extra}# Encoding: {'IAST, converted from the Devanagari OCR with indic_transliteration' if enc == 'iast' else 'Devanagari as OCR’d'}.\n\n"
        dest.write_text(hdr + body(book, who, enc))
        src = P / "etext" / f"{book}_{who}{'.iast' if enc == 'iast' else ''}.txt"
        log.append((str(src), str(dest.relative_to(LIB)),
                    "new OCR e-text (Surya OCR 2; mūla located via Das & Emmerick, commentaries split by sigla; "
                    "see /mnt2/kengo/ocr-ahs-tika1928/README.md), user-requested " + datetime.date.today().isoformat()))
        print("installed", dest.relative_to(LIB), dest.stat().st_size)
(LIB / "catalog" / f"move_log_{ts}_ahs_commentaries_ocr.tsv").write_text("\n".join("\t".join(r) for r in log) + "\n")
print("log:", f"catalog/move_log_{ts}_ahs_commentaries_ocr.tsv")
