#!/usr/bin/env python3
"""Text reuse among the Sanskrit AHS commentaries (Candranandana, Aruṇadatta, Hemādri).
Letters-only normalised IAST (spaces, punctuation, visarga, anusvāra and pre-consonantal nasals dropped;\ngeminates simplified — the Parāḍkar OCR loses most anusvāra/visarga dots), K-char shingles.
A position of commentary A is "shared with B" if a shingle covering it occurs in B; covered stretches
(gaps ≤ GAP bridged) of ≥ MINRUN letters are runs. Each run is classified by what else contains it:
  mula   — ≥ 50 % of its shingles occur in the AHS root text (lemmata, quoted verses of the root)
  source — ≥ 50 % occur in the other āyurveda texts of the library (Caraka, Suśruta, Saṃgraha, Cakrapāṇi …)
  comm   — otherwise: wording found only in the two commentaries → borrowing (or common lost source)
Same-verse locality: whether the B side of the run is attached to the same root verse (± 3 verses).
Usage: python3 -P reuse.py OUT_JSON
"""
import json, re, sys, glob, unicodedata
from collections import defaultdict
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

P = "/mnt2/kengo/ocr-ahs-tika1928"
AY = "/mnt2/kengo/E-texts/1_sanskr/6_sastra/7_ayur"
K, GAP, MINRUN = 24, 6, 40
out_f = sys.argv[1]

def norm(t):
    t = unicodedata.normalize("NFC", t.lower())
    t = re.sub(r"[^a-zāīūṛṝḷēōṭḍśṣṃṅñṇḥ]", "", t.replace("ḥ", "").replace("ṃ", ""))
    t = re.sub(r"[ṅñṇnm](?=[kgcjṭḍtdpbśṣsyrlvh])", "", t)   # OCR drops anusvāra; class nasal ~ anusvāra
    return re.sub(r"([kgcjṭḍtdpbmy])\1", r"\1", re.sub(r"(?<=r)([kgcjṭḍtdpbmyvśṣs])\1", r"\1", t))  # rdh/rddh, tt/t
def shingles(s): return {hash(s[i:i + K]) for i in range(len(s) - K + 1)}

# ---- commentaries as letter streams with per-letter verse index
order = {}
def verse_of(ref):
    r = re.sub(r"(ab|cd|ef|gh)$", "", ref or "")
    m = re.match(r"(\w+)\.(\d+)\.(\d+)", r)
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else None
def load(book, who, chapters=None):
    s, vs = [], []
    for l in open(f"{P}/etext/{book}_structure.jsonl"):
        x = json.loads(l)
        if x["type"] != "comm" or x.get("who") != who: continue
        v = verse_of(x["ref"])
        if not v or (chapters and (v[0], v[1]) not in chapters): continue
        n = norm(transliterate(x["text"], sanscript.DEVANAGARI, sanscript.IAST))
        s.append(n); vs += [v] * len(n)
    return "".join(s), vs

# ---- reference corpora
def lib(files):
    S = set()
    for f in files:
        S |= shingles(norm(open(f, errors="ignore").read()))
    return S
mula_files = [f"{AY}/{f}" for f in ("vagbhata_astangahrdaya.txt", "vagbhata_astangahrdaya_b.txt",
              "vagbhata_astangahrdaya_c.txt", "unknown_vagbhata-astangahrdaya_from_arlo.txt")]
src_files = [f for f in glob.glob(f"{AY}/*.txt") if f not in mula_files and not re.search(
    r"meulenbeld|arunadatta|hemadri|candranandana|readme", f)]
MULA = lib(mula_files)
for b in ("t1928", "parad"):   # OCR'd mūla of both editions (same OCR noise as the commentaries)
    MULA |= shingles(norm(transliterate(open(f"{P}/etext/{b}_mula.txt").read(), sanscript.DEVANAGARI, sanscript.IAST)))
SRC = lib(src_files)
print("ref shingles: mula", len(MULA), "src", len(SRC), "files", len(src_files), flush=True)

def runs(a, b_set):
    cov = bytearray(len(a))
    for i in range(len(a) - K + 1):
        if hash(a[i:i + K]) in b_set: cov[i:i + K] = b"\1" * K
    out, i = [], 0
    while i < len(a):
        if cov[i]:
            j = i
            while True:
                while j < len(a) and cov[j]: j += 1
                k = j
                while k < len(a) and k - j <= GAP and not cov[k]: k += 1
                if k < len(a) and k - j <= GAP and cov[k]: j = k; continue
                break
            if j - i >= MINRUN: out.append((i, j))
            i = j
        else: i += 1
    return out

def classify(seg):
    sh = [hash(seg[i:i + K]) for i in range(len(seg) - K + 1)]
    fm = sum(h in MULA for h in sh) / len(sh); fs = sum(h in SRC for h in sh) / len(sh)
    return "mula" if fm >= .5 else "source" if fs >= .5 else "comm"

def compare(nameA, A, nameB, B):
    a, va = A; b, vb = B
    bpos = defaultdict(list)
    for i in range(0, len(b) - K + 1): bpos[hash(b[i:i + K])].append(i)
    R = runs(a, set(bpos))
    tot = defaultdict(int); local = defaultdict(int); ex = []
    for i, j in R:
        seg = a[i:j]; c = classify(seg); tot[c] += j - i
        # locality: B positions of the run's first shingles
        hits = [p for q in range(i, min(j - K, i + 200) + 1, 8) for p in bpos.get(hash(a[q:q + K]), [])[:5]]
        same = any(vb[p][:2] == va[i][:2] and abs(vb[p][2] - va[i][2]) <= 3 for p in hits)
        if same: local[c] += j - i
        if c == "comm": ex.append({"len": j - i, "verse": "%s.%d.%d" % va[i], "same_verse": same, "text": seg[:300]})
    ex.sort(key=lambda e: -e["len"])
    L = len(a)
    res = {"A": nameA, "B": nameB, "letters_A": L,
           **{f"pct_{c}": round(100 * tot[c] / L, 2) for c in ("mula", "source", "comm")},
           **{f"pct_{c}_same_verse": round(100 * local[c] / max(tot[c], 1), 1) for c in ("mula", "source", "comm")},
           "runs_comm": len([e for e in ex]), "runs_comm_ge100": sum(e["len"] >= 100 for e in ex),
           "examples": ex[:25]}
    print(f"{nameA:28s} ← {nameB:28s} letters {L:8d} | mūla {res['pct_mula']:5.1f}% | sources {res['pct_source']:5.1f}% "
          f"| commentary-only {res['pct_comm']:5.1f}% ({res['pct_comm_same_verse']}% same verse; {res['runs_comm']} runs, "
          f"{res['runs_comm_ge100']} ≥100)", flush=True)
    return res

# Sūtrasthāna, 1928 edition: all three commentators printed together
CN = load("t1928", "candranandana"); AR = load("t1928", "arunadatta"); HE = load("t1928", "hemadri")
results = {"params": {"K": K, "GAP": GAP, "MINRUN": MINRUN}, "pairs": []}
for (na, A), (nb, B) in [(("Aruṇadatta Sū", AR), ("Candranandana Sū", CN)), (("Candranandana Sū", CN), ("Aruṇadatta Sū", AR)),
                         (("Hemādri Sū", HE), ("Candranandana Sū", CN)), (("Candranandana Sū", CN), ("Hemādri Sū", HE)),
                         (("Hemādri Sū", HE), ("Aruṇadatta Sū", AR)), (("Aruṇadatta Sū", AR), ("Hemādri Sū", HE))]:
    results["pairs"].append(compare(na, A, nb, B))
# Rest of the work, Parāḍkar edition: Aruṇadatta vs Hemādri where both are printed (outside Sū)
hch = {verse_of(json.loads(l)["ref"])[:2] for l in open(f"{P}/etext/parad_structure.jsonl")
       if json.loads(l)["type"] == "comm" and json.loads(l).get("who") == "hemadri" and verse_of(json.loads(l)["ref"])}
hch = {c for c in hch if c[0] != "Sū"}
AR2 = load("parad", "arunadatta", hch); HE2 = load("parad", "hemadri", hch)
print("Parāḍkar non-Sū chapters with Hemādri:", sorted(hch))
results["parad_chapters"] = sorted("%s.%d" % c for c in hch)
results["pairs"].append(compare("Hemādri (Ni/Ci/Ka)", HE2, "Aruṇadatta (Ni/Ci/Ka)", AR2))
results["pairs"].append(compare("Aruṇadatta (Ni/Ci/Ka)", AR2, "Hemādri (Ni/Ci/Ka)", HE2))
# Candranandana excerpts (U.21–22) vs Aruṇadatta's same chapters
uch = {("U", 21), ("U", 22)}
results["pairs"].append(compare("Candranandana U.21–22", load("parad", "candranandana", uch), "Aruṇadatta U.21–22", load("parad", "arunadatta", uch)))
# Control: same commentator, two editions (upper bound for OCR-noisy identity)
results["pairs"].append(compare("Aruṇadatta Sū 1928", AR, "Aruṇadatta Sū Parāḍkar", load("parad", "arunadatta", {(c[0], c[1]) for c in set(AR[1])})))
json.dump(results, open(out_f, "w"), ensure_ascii=False, indent=1)
