# Full census of verbatim overlap between the Tengyur AHS (D4310), the Vaiḍūryakabhāṣya (D4311),
# and the Rgyud bzhi. Exact syllable n-grams after Wylie normalisation; grams frequent in either
# text are dropped as stock phrases.
# usage: rgyud_census.py PAGES_DIR RGYUD_DIR OUT_JSON [N]
import glob, json, re, sys
from collections import defaultdict, Counter
sys.path.insert(0, sys.argv[0].rsplit("/bin/", 1)[0] + "/py")
import pyewts

pages, rdir, out = sys.argv[1], sys.argv[2], sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 6
MAXF = 3
conv = pyewts.pyewts()

def syls(w):
    w = w.lower().replace("+", "")
    w = re.sub(r"[/|;:!@#*_\[\]()«»<>0-9\\-]+", " ", w)
    return [s for s in w.split() if s]

def segs(fn):
    for p in sorted(glob.glob(f"{pages}/{fn}.*.json")):
        for it in json.load(open(p))["items"]:
            yield it["segnr"], "".join(x["text"] for x in it["segtext"])

# --- D4310 with chapter labels (count sequentially within each sthāna; numerals are unreliable)
STH = [("phyi ma'i", "U"), ("cho ga grub pa'i", "Ka"), ("gso ba'i gnas", "Ci"), ("nad gzhi'i gnas", "Ni"),
       ("lus kyi gnas", "Śā"), ("mdo'i gnas", "Sū")]
COLO = re.compile(r"le'u (ste )?[^/]*?'o")
# two passes: a chapter's text precedes its colophon, so each segment takes the label of the
# next colophon at or after it
S10 = list(segs("BO_T13_D4310"))
count, labels = Counter(), [None] * len(S10)
for k, (_, t) in enumerate(S10):
    if not COLO.search(t):
        continue
    ctx = (S10[k - 1][1] if k else "") + " " + t
    st = next((ab for key, ab in STH if key in t), None) or \
         (next((ab for key, ab in STH if key in ctx), None) if "bsdus pa las" in ctx else None)
    if st:
        count[st] += 1
        labels[k] = f"{st}.{count[st]}"
nxt = "U.40"
for k in range(len(S10) - 1, -1, -1):
    nxt = labels[k] or nxt
    labels[k] = nxt
A, Apos = [], []
for (segnr, t), label in zip(S10, labels):
    for s in syls(t):
        A.append(s); Apos.append((segnr, label))
chap_counts = dict(count)

# --- D4311 (both parts)
B = []
for fn in ("BO_T13_D4311", "BO_T13_D4311-2"):
    for _, t in segs(fn):
        B.extend(syls(t))

# --- Rgyud bzhi, labelled by tantra and chapter
def wylie_file(b):
    return conv.toWylie(open(glob.glob(f"{rdir}/MonlamAI_{b}/*.txt")[0], encoding="utf-8").read())
rtsa_full = wylie_file("BO4623")
cut = rtsa_full.find("rtsa ba'i rgyud ces bya ba rdzogs")
parts = [("Rtsa", rtsa_full[:cut + 40]), ("Bshad", wylie_file("BO2889")),
         ("Man ngag (1-27)", wylie_file("BO5092")), ("Phyi", wylie_file("BO5093"))]
R, Rpos, tantra_len = [], [], {}
for name, w in parts:
    ch = 1
    n0 = len(R)
    for chunk in re.split(r"(le'u ste [^/]*?'o)", w):
        if re.match(r"le'u ste [^/]*?'o", chunk):
            for s in syls(chunk): R.append(s); Rpos.append((name, ch))
            ch += 1
            continue
        for s in syls(chunk):
            R.append(s); Rpos.append((name, ch))
    tantra_len[name] = len(R) - n0

def grams(seq):
    d = defaultdict(list)
    for i in range(len(seq) - N + 1):
        d[tuple(seq[i:i + N])].append(i)
    return d
gA, gB, gR = grams(A), grams(B), grams(R)
ok = lambda g: len(gR[g]) <= MAXF and len(gA.get(g, [])) <= MAXF

shared_AR = {g for g in gA if g in gR and ok(g)}
shared_BR = {g for g in gB if g in gR and len(gR[g]) <= MAXF and len(gB[g]) <= MAXF}
cls = {"all three": shared_AR & shared_BR, "D4310 only": shared_AR - shared_BR, "D4311 only": shared_BR - shared_AR}

# --- cluster D4310↔Rgyud hits into passages
hits = sorted((gA[g][0], gR[g][0], g) for g in shared_AR)
P = []
for i, j, g in hits:
    if P and i - P[-1]["ae"] <= N + 3 and abs((j - P[-1]["re"]) - (i - P[-1]["ae"])) <= 15:
        P[-1]["ae"], P[-1]["re"] = i, j; P[-1]["g"].append(g)
    else:
        P.append({"as": i, "ae": i, "rs": j, "re": j, "g": [g]})
for p in P:
    p["len"] = p["ae"] - p["as"] + N
    p["ahs_seg"], p["ahs_ch"] = Apos[p["as"]]
    p["rgyud"] = f"{Rpos[p['rs']][0]} ch.{Rpos[p['rs']][1]}"
    p["tantra"] = Rpos[p["rs"]][0]
    in_b = sum(1 for g in p["g"] if g in shared_BR)
    p["d4311_share"] = round(in_b / len(p["g"]), 2)
    p["ahs_text"] = " ".join(A[p["as"]:p["ae"] + N])
    p["rgyud_text"] = " ".join(R[p["rs"]:p["re"] + N])
    del p["g"]

# --- three-way test, census side: for each verse the Rgyud bzhi shares verbatim with D4310,
# does D4311 have it identically, in a different rendering, or not at all?
bg = lambda s: [tuple(s[i:i + 2]) for i in range(len(s) - 1)]
BB = bg(B)
fB = Counter(BB); stopB = {b for b, n in fB.items() if n > 50}
iB = defaultdict(list)
for i, b in enumerate(BB): iB[b].append(i)
for p in P:
    a = A[p["as"]:p["ae"] + N]
    ba = set(bg(a)) - stopB
    cand = Counter()
    for b in ba:
        if len(iB[b]) <= 20:
            for j in iB[b]: cand[j // 6] += 1
    if not ba or not cand:
        p["d4311_recall"], p["d4311_class"], p["d4311_text"] = 0.0, "absent", ""
        continue
    best = max(cand, key=cand.get) * 6
    win = BB[max(0, best - len(a) - 6): best + len(a) + 6]
    rec = len(ba & set(win)) / len(ba)
    p["d4311_recall"] = round(rec, 2)
    p["d4311_class"] = "same wording" if rec >= 0.8 else "different rendering" if rec >= 0.3 else "absent"
    p["d4311_text"] = " ".join(B[max(0, best - 3): best + len(a) + 3])

# coverage of Rgyud bzhi syllables by D4310-shared passages
covered = [False] * len(R)
for g in shared_AR:
    for j in gR[g]:
        for k in range(j, j + N): covered[k] = True
cov_t = Counter(); cov_ch = Counter(); src_ch = defaultdict(Counter)
for k, c in enumerate(covered):
    if c:
        cov_t[Rpos[k][0]] += 1; cov_ch[f"{Rpos[k][0]} ch.{Rpos[k][1]}"] += 1
for p in P:
    src_ch[p["rgyud"]][p["ahs_ch"]] += p["len"]
ahs_ch = Counter()
for p in P: ahs_ch[p["ahs_ch"]] += p["len"]

# D4311-only passages (clusters of grams shared with Rgyud but absent from D4310), minus formulaic
# noise: chapter colophons, drug lists joined by "dang", and the tathāgata homage
noise = lambda g: "le'u" in g or g.count("dang") >= 2 or "sangs" in g or "rgyas" in g or "rdzogs" in g
cls["D4311 only (filtered)"] = {g for g in cls["D4311 only"] if not noise(g)}
cls["D4310 only (filtered)"] = {g for g in cls["D4310 only"] if not noise(g)}
hb = sorted((gB[g][0], gR[g][0]) for g in cls["D4311 only (filtered)"])
PB = []
for i, j in hb:
    if PB and i - PB[-1][1] <= N + 3: PB[-1][1] = i
    else: PB.append([i, i, j])
PB = [{"len": e - s + N, "rgyud": f"{Rpos[j][0]} ch.{Rpos[j][1]}", "d4311_text": " ".join(B[s:e + N]),
       "rgyud_text": " ".join(R[j:j + (e - s) + N])} for s, e, j in PB]

res = {"N": N, "max_freq": MAXF, "syllables": {"D4310": len(A), "D4311": len(B), "Rgyud": len(R), "by_tantra": tantra_len},
       "d4310_chapters_detected": chap_counts,
       "gram_classes": {k: len(v) for k, v in cls.items()},
       "n_passages": len(P), "shared_syllables_in_D4310": sum(p["len"] for p in P),
       "passage_tiers": {"single line (<12 syl)": sum(1 for p in P if p["len"] < 12),
                         "multi-line (>=12 syl)": sum(1 for p in P if p["len"] >= 12)},
       "d4311_classes": dict(Counter(p["d4311_class"] for p in P)),
       "d4311_classes_multiline": dict(Counter(p["d4311_class"] for p in P if p["len"] >= 12)),
       "coverage_by_tantra": {t: {"covered": cov_t[t], "total": tantra_len[t], "pct": round(100 * cov_t[t] / tantra_len[t], 2)} for t in tantra_len},
       "top_rgyud_chapters": [(c, n, dict(src_ch[c].most_common(4))) for c, n in cov_ch.most_common(40)],
       "ahs_chapters": ahs_ch.most_common(),
       "passages": sorted(P, key=lambda p: -p["len"]),
       "d4311_only_passages": sorted(PB, key=lambda p: -p["len"])[:60]}
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ("syllables", "d4310_chapters_detected", "gram_classes", "n_passages", "passage_tiers", "d4311_classes", "d4311_classes_multiline",
                                       "shared_syllables_in_D4310", "coverage_by_tantra")}, ensure_ascii=False, indent=1))
