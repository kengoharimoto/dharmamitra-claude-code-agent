#!/usr/bin/env python3
"""Sentence-level (fuzzy) text reuse among the Sanskrit AHS commentaries — robust to OCR noise.
Each daṇḍa-delimited sentence (≥ MINLEN normalised letters) of commentary A is scored with
rapidfuzz.partial_ratio against B's commentary on the same root verse ± WIN (same chapter).
  shared   score ≥ T_SHARED      verbatim  score ≥ T_VERB
Calibration: control = the same commentary in the other edition (should be ≈ all shared);
null = B's commentary on verses of a different chapter (false-positive rate).
Shared sentences are tagged "quotation" when ≥ 40 % of their 16-letter shingles occur in the other
āyurveda texts of the library or in the AHS root text, otherwise "commentary".
Usage: python3 -P reuse2.py OUT_JSON
"""
import json, re, sys, glob, random
from collections import defaultdict, Counter
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
sys.path.insert(0, "/mnt2/kengo/ocr-ahs-tika1928")
P = "/mnt2/kengo/ocr-ahs-tika1928"; AY = "/mnt2/kengo/E-texts/1_sanskr/6_sastra/7_ayur"
MINLEN, WIN, T_SHARED, T_VERB, KQ = 30, 3, 85, 95, 16
out_f = sys.argv[1]
random.seed(1)

def norm(t):
    import unicodedata
    t = unicodedata.normalize("NFC", t.lower())
    t = re.sub(r"[^a-zāīūṛṝḷēōṭḍśṣṃṅñṇḥ]", "", t.replace("ḥ", "").replace("ṃ", ""))
    t = re.sub(r"[ṅñṇnm](?=[kgcjṭḍtdpbśṣsyrlvh])", "", t)
    return re.sub(r"([kgcjṭḍtdpbmy])\1", r"\1", re.sub(r"(?<=r)([kgcjṭḍtdpbmyvśṣs])\1", r"\1", t))
def verse_of(ref):
    m = re.match(r"(\w+)\.(\d+)\.(\d+)", re.sub(r"(ab|cd|ef|gh)$", "", ref or ""))
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else None

def load(book, who, chapters=None):
    """-> {verse: [raw IAST passages]}"""
    by = defaultdict(list)
    for l in open(f"{P}/etext/{book}_structure.jsonl"):
        x = json.loads(l)
        if x["type"] != "comm" or x.get("who") != who: continue
        v = verse_of(x["ref"])
        if not v or (chapters is not None and v[:2] not in chapters): continue
        by[v].append(transliterate(x["text"], sanscript.DEVANAGARI, sanscript.IAST))
    return by
def sentences(by):
    out = []
    for v, ps in by.items():
        buf = ""
        for piece in re.split(r"[|।॥]+|\(\d+\)|\d+", " ".join(ps)):
            buf += " " + piece
            if len(norm(buf)) >= MINLEN: out.append((v, buf.strip(), norm(buf))); buf = ""
    return out
def windows(by):
    nb = {v: norm(" ".join(ps)) for v, ps in by.items()}
    ch = defaultdict(list)
    for v in nb: ch[v[:2]].append(v)
    def win(v):
        return "".join(nb[u] for u in sorted(ch.get(v[:2], [])) if abs(u[2] - v[2]) <= WIN)
    return win, ch

def kset(files, deva=False):
    S = set()
    for f in files:
        t = open(f, errors="ignore").read()
        if deva: t = transliterate(t, sanscript.DEVANAGARI, sanscript.IAST)
        n = norm(t); S |= {hash(n[i:i + KQ]) for i in range(len(n) - KQ + 1)}
    return S
REF = kset([f for f in glob.glob(f"{AY}/*.txt") if not re.search(r"meulenbeld|arunadatta|hemadri|candranandana|readme", f)])
REF |= kset([f"{P}/etext/t1928_mula.txt", f"{P}/etext/parad_mula.txt"], deva=True)
def is_quote(n):
    sh = [hash(n[i:i + KQ]) for i in range(len(n) - KQ + 1)]
    return sum(h in REF for h in sh) / max(len(sh), 1) >= .4

def compare(nameA, A, nameB, B, null=True, keep=40):
    S = sentences(A); win, chB = windows(B)
    chapters = list(chB)
    sc, scn, rows = [], [], []
    for v, raw, n in S:
        w = win(v)
        s = fuzz.partial_ratio(n, w) if w else 0
        sc.append(s)
        if null:
            other = [c for c in chapters if c != v[:2]]
            if other:
                c = random.choice(other); u = random.choice(chB[c])
                wn = win((c[0], c[1], u[2]))
                scn.append(fuzz.partial_ratio(n, wn) if wn else 0)
        if s >= T_SHARED: rows.append((v, raw, n, s))
    L = sum(len(n) for _, _, n in S)
    shared_L = sum(len(n) for _, _, n, _ in rows)
    verb_L = sum(len(n) for _, _, n, s in rows if s >= T_VERB)
    q = [is_quote(n) for _, _, n, _ in rows]
    comm_L = sum(len(r[2]) for r, qq in zip(rows, q) if not qq)
    # per-chapter share (letters) of commentary-only reuse
    perch = defaultdict(lambda: [0, 0])
    for v, _, n in S: perch["%s.%d" % v[:2]][1] += len(n)
    for (v, _, n, _), qq in zip(rows, q):
        if not qq: perch["%s.%d" % v[:2]][0] += len(n)
    res = {"A": nameA, "B": nameB, "sentences": len(S), "letters": L,
           "pct_shared": round(100 * shared_L / L, 1), "pct_verbatim": round(100 * verb_L / L, 1),
           "pct_shared_commentary_only": round(100 * comm_L / L, 1),
           "pct_shared_quotation": round(100 * (shared_L - comm_L) / L, 1),
           "null_pct_shared": round(100 * sum(x >= T_SHARED for x in scn) / max(len(scn), 1), 1) if null else None,
           "per_chapter_pct_commentary_only": {k: round(100 * a / b, 1) for k, (a, b) in sorted(perch.items()) if b > 2000},
           "examples": [{"verse": "%s.%d.%d" % v, "score": s, "quote": qq, "text": raw[:400]}
                        for (v, raw, n, s), qq in sorted(zip(rows, q), key=lambda z: -len(z[0][2]))[:keep]]}
    print(f"{nameA:30s} ← {nameB:30s} sent {len(S):6d} | shared {res['pct_shared']:5.1f}% (verbatim {res['pct_verbatim']:5.1f}%) "
          f"| commentary-only {res['pct_shared_commentary_only']:5.1f}% quotation {res['pct_shared_quotation']:5.1f}% "
          f"| null {res['null_pct_shared']}%", flush=True)
    return res

CN, AR, HE = (load("t1928", w) for w in ("candranandana", "arunadatta", "hemadri"))
sū = {v[:2] for v in AR}
AR_p = load("parad", "arunadatta", sū); HE_p = load("parad", "hemadri", sū)
R = {"params": dict(MINLEN=MINLEN, WIN=WIN, T_SHARED=T_SHARED, T_VERB=T_VERB, KQ=KQ), "pairs": []}
print("== control: same commentary, two editions")
R["pairs"].append(compare("Aruṇadatta Sū 1928", AR, "Aruṇadatta Sū Parāḍkar", AR_p))
R["pairs"].append(compare("Hemādri Sū 1928", HE, "Hemādri Sū Parāḍkar", HE_p))
print("== Sūtrasthāna, 1928 edition")
for (na, A), (nb, B) in [(("Aruṇadatta", AR), ("Candranandana", CN)), (("Candranandana", CN), ("Aruṇadatta", AR)),
                         (("Hemādri", HE), ("Candranandana", CN)), (("Candranandana", CN), ("Hemādri", HE)),
                         (("Hemādri", HE), ("Aruṇadatta", AR)), (("Aruṇadatta", AR), ("Hemādri", HE))]:
    R["pairs"].append(compare(na + " Sū", A, nb + " Sū", B))
print("== outside Sū, Parāḍkar edition")
hch = {v[:2] for v in load("parad", "hemadri") if v[0] != "Sū"}
AR2, HE2 = load("parad", "arunadatta", hch), load("parad", "hemadri", hch)
R["pairs"].append(compare("Hemādri Ni/Ci/Ka/Śā", HE2, "Aruṇadatta Ni/Ci/Ka/Śā", AR2))
R["pairs"].append(compare("Aruṇadatta Ni/Ci/Ka/Śā", AR2, "Hemādri Ni/Ci/Ka/Śā", HE2))
uch = {v[:2] for v in load("parad", "candranandana")}
R["pairs"].append(compare("Candranandana (Parāḍkar excerpts)", load("parad", "candranandana"), "Aruṇadatta same chapters", load("parad", "arunadatta", uch)))
json.dump(R, open(out_f, "w"), ensure_ascii=False, indent=1)
