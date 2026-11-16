#!/usr/bin/env python3
"""Find a Devanagari (or IAST) snippet in parallel texts, to restore letters lost at a clipped column edge.
Usage: python3 -P parallel.py "SNIPPET" [--top N]
Searches: Parāḍkar Aruṇadatta/Hemādri (other edition), the 1928 streams of all three commentators,
the AHS root text (Das & Emmerick), Aṣṭāṅgasaṃgraha, Carakasaṃhitā, Suśrutasaṃhitā.
Prints for each source the best-matching stretch (Devanagari) with its score (0-100)."""
import sys, re, unicodedata
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
P = "/mnt2/kengo/ocr-ahs-tika1928/etext"; AY = "/mnt2/kengo/E-texts/1_sanskr/6_sastra/7_ayur"
SRC = {"Parāḍkar Aruṇadatta": f"{P}/parad_arunadatta.txt", "Parāḍkar Hemādri": f"{P}/parad_hemadri.txt",
       "1928 Aruṇadatta": f"{P}/t1928_arunadatta.txt", "1928 Candranandana": f"{P}/t1928_candranandana.txt",
       "1928 Hemādri": f"{P}/t1928_hemadri.txt", "1928 mūla": f"{P}/t1928_mula.txt",
       "AHS (Das & Emmerick)": f"{AY}/vagbhata_astangahrdaya.txt"}
import glob
for k, pat in (("Aṣṭāṅgasaṃgraha", "*samgraha*"), ("Caraka", "agnivesa_carakasamhita.txt"), ("Suśruta", "susruta*")):
    fs = sorted(glob.glob(f"{AY}/{pat}"))
    if fs: SRC[k] = fs[0]
q = sys.argv[1]
top = 1
def deva(t): return t if re.search(r"[ऀ-ॿ]", t) else transliterate(t, sanscript.IAST, sanscript.DEVANAGARI)
def key(t):  # compare on Devanagari letters only
    return re.sub(r"[^अ-हा-्ॐ-ॣ]", "", unicodedata.normalize("NFC", t)).replace("ं", "").replace("ः", "")
qk = key(deva(q))
for name, f in SRC.items():
    t = open(f, errors="ignore").read()
    if not re.search(r"[ऀ-ॿ]", t[:20000]): t = deva(t)
    # map key positions back to the raw text
    idx = [i for i, c in enumerate(t) if key(c)]
    k = "".join(t[i] for i in idx)
    k2 = k.replace("ं", "").replace("ः", "")  # (already dropped by key)
    al = fuzz.partial_ratio_alignment(qk, k, score_cutoff=0)
    if not al: continue
    a, b = idx[max(al.dest_start - 40, 0)], idx[min(al.dest_end + 40, len(idx) - 1)]
    print(f"[{al.score:5.1f}] {name}: …{t[a:b+1].replace(chr(10),' ')}…")
