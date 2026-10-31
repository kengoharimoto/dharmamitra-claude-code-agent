import sys, json, glob, re
from collections import defaultdict
src = open("/mnt2/kengo/ocr-ahs-tika1928/reuse2.py").read().split("REF = kset")[0]
sys.argv = ["x", "/dev/null"]; exec(src)
K = 20
AY = "/mnt2/kengo/E-texts/1_sanskr/6_sastra/7_ayur"
GROUPS = {"Caraka": "agnivesa_*", "Suśruta": "susruta_*", "Aṣṭāṅgasaṃgraha": "vagbhata_astangasamgraha*",
          "Cakrapāṇi (Āyurvedadīpikā)": "cakrapani_*", "Jejjaṭa (Nirantarapadavyākhyā)": "unknown_nirantarapadavyakhya*",
          "Mādhavanidāna": "madhavakara_*", "Nighaṇṭus": "*nighantu*", "AHS root": "vagbhata_astangahrdaya*"}
G = {}
for g, pat in GROUPS.items():
    S = set()
    for f in glob.glob(f"{AY}/{pat}.txt"):
        n = norm(open(f, errors="ignore").read()); S |= {hash(n[i:i+K]) for i in range(len(n)-K+1)}
    G[g] = S
mula = set()
for b in ("t1928", "parad"):
    n = norm(transliterate(open(f"/mnt2/kengo/ocr-ahs-tika1928/etext/{b}_mula.txt").read(), sanscript.DEVANAGARI, sanscript.IAST))
    mula |= {hash(n[i:i+K]) for i in range(len(n)-K+1)}
G["AHS root"] |= mula
def stream(by):
    s, vs = [], []
    for v in sorted(by):
        n = norm(" ".join(by[v])); s.append(n); vs += [v]*len(n)
    return "".join(s), vs
def census(name, by):
    a, vs = stream(by); res = {}; spots = {}
    for g, S in G.items():
        cov = bytearray(len(a))
        for i in range(len(a)-K+1):
            if hash(a[i:i+K]) in S: cov[i:i+K] = b"\1"*K
        # keep only runs ≥ 40 letters
        tot, i, sp = 0, 0, set()
        while i < len(a):
            if cov[i]:
                j = i
                while j < len(a) and cov[j]: j += 1
                if j - i >= 40: tot += j - i; sp.add(vs[i])
                i = j
            else: i += 1
        res[g] = round(100*tot/len(a), 2); spots[g] = sp
    print(f"{name:34s} letters {len(a):7d} | " + " | ".join(f"{g} {p}" for g, p in res.items()), flush=True)
    return res, spots
CN, AR, HE = (load("t1928", w) for w in ("candranandana", "arunadatta", "hemadri"))
out = {}
spots = {}
for n, by in (("Candranandana Sū (1928)", CN), ("Aruṇadatta Sū (1928)", AR), ("Hemādri Sū (1928)", HE)):
    out[n], spots[n] = census(n, by)
hch = {v[:2] for v in load("parad", "hemadri") if v[0] != "Sū"}
out["Aruṇadatta Ni/Ci/Ka/Śā (Parāḍkar, Hemādri's chapters)"], _ = census("Aruṇadatta Ni/Ci/Ka/Śā (Par.)", load("parad", "arunadatta", hch))
out["Hemādri Ni/Ci/Ka/Śā (Parāḍkar)"], _ = census("Hemādri Ni/Ci/Ka/Śā (Par.)", load("parad", "hemadri", hch))
out["Aruṇadatta whole (Parāḍkar)"], _ = census("Aruṇadatta whole (Par.)", load("parad", "arunadatta"))
# same source quoted at the same verse by two commentators (Sū)
names = list(spots); shared = {}
for g in GROUPS:
    if g == "AHS root": continue
    for i in range(3):
        for j in range(i+1, 3):
            a, b = spots[names[i]][g], spots[names[j]][g]
            if a and b: shared[f"{g}: {names[i].split()[0]}∩{names[j].split()[0]}"] = [len(a), len(b), len(a & b)]
print("verses where a source is quoted [A, B, both]:"); [print(" ", k, v) for k, v in shared.items()]
json.dump({"K": K, "minrun": 40, "pct_letters_quoting": out, "same_verse_same_source": shared},
          open("/mnt2/kengo/ocr-ahs-tika1928/check/reuse_sources.json", "w"), ensure_ascii=False, indent=1)
