# Line-level fuzzy estimate of how much of each Rgyud bzhi tantra is recast from the Tengyur AHS.
# A Rgyud line counts as "AHS-related" when >= THR of its distinctive syllable bigrams occur in one
# window of D4310 of comparable length. Control: the same lines against D4310 with each window's
# syllables drawn from a random distant chapter (shuffled-window baseline).
# usage: rgyud_fuzzy.py PAGES_DIR RGYUD_DIR OUT_JSON [THR]
import glob, json, random, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, sys.argv[0].rsplit("/bin/", 1)[0] + "/py")
import pyewts

pages, rdir, out = sys.argv[1:4]
THR = float(sys.argv[4]) if len(sys.argv) > 4 else 0.6
MIN_BG = 5
conv = pyewts.pyewts()

def syls(w):
    w = w.lower().replace("+", "")
    w = re.sub(r"[/|;:!@#*_\[\]()«»<>0-9\\-]+", " ", w)
    return [s for s in w.split() if s]
bg = lambda s: [tuple(s[i:i + 2]) for i in range(len(s) - 1)]

A = []
for p in sorted(glob.glob(f"{pages}/BO_T13_D4310.*.json")):
    for it in json.load(open(p))["items"]:
        A.extend(syls("".join(x["text"] for x in it["segtext"])))
AB = bg(A)
fA = Counter(AB)
iA = defaultdict(list)
for i, b in enumerate(AB): iA[b].append(i)

def wylie_file(b):
    return conv.toWylie(open(glob.glob(f"{rdir}/MonlamAI_{b}/*.txt")[0], encoding="utf-8").read())
rtsa = wylie_file("BO4623"); rtsa = rtsa[:rtsa.find("rtsa ba'i rgyud ces bya ba rdzogs") + 40]
parts = [("Rtsa", rtsa), ("Bshad", wylie_file("BO2889")), ("Man ngag (1-27)", wylie_file("BO5092")), ("Phyi", wylie_file("BO5093"))]

# stop bigrams: frequent in either corpus
fR = Counter()
lines = []
for name, w in parts:
    ch = 1
    for raw in re.split(r"/+_?/*", w):
        s = syls(raw)
        if re.search(r"le'u ste [^/]*?'o", raw): ch += 1
        if s: lines.append((name, ch, s)); fR.update(bg(s))
STOP = {b for b, n in fA.items() if n > 40} | {b for b, n in fR.items() if n > 40}

def best_recall(s, rng=None):
    bs = set(bg(s)) - STOP
    if len(bs) < MIN_BG: return None, None
    cand = Counter()
    for b in bs:
        if len(iA[b]) <= 25:
            for j in iA[b]: cand[j // 10] += 1
    if not cand: return 0.0, None
    L = len(s) * 2 + 10
    best_j, best_r = None, 0.0
    for c, _ in cand.most_common(5):
        j = c * 10
        if rng is not None:                      # control: same-size window from a random far-away place
            j = (j + rng.randrange(len(AB) // 4, 3 * len(AB) // 4)) % len(AB)
        win = set(AB[max(0, j - L): j + L])
        r = len(bs & win) / len(bs)
        if r > best_r: best_j, best_r = j, r
    return best_r, best_j

rng = random.Random(1)
tot, rel, ctl = Counter(), Counter(), Counter()
by_ch = defaultdict(lambda: [0, 0])
samples = defaultdict(list)
for name, ch, s in lines:
    r, j = best_recall(s)
    if r is None: continue
    n = len(s)
    tot[name] += n
    by_ch[f"{name} ch.{ch}"][1] += n
    if r >= THR:
        rel[name] += n; by_ch[f"{name} ch.{ch}"][0] += n
        band = "0.6-0.7" if r < 0.7 else "0.7-0.85" if r < 0.85 else ">=0.85"
        if len(samples[band]) < 400:
            samples[band].append({"tantra": f"{name} ch.{ch}", "recall": round(r, 2), "rgyud": " ".join(s),
                                  "ahs": " ".join(A[max(0, j - 4): j + len(s) + 8])})
    rc, _ = best_recall(s, rng)
    if rc is not None and rc >= THR: ctl[name] += n

res = {"threshold": THR, "by_tantra": {t: {"assessed_syllables": tot[t], "ahs_related": rel[t], "pct": round(100 * rel[t] / tot[t], 1),
                                           "control_pct": round(100 * ctl[t] / tot[t], 1)} for t in tot},
       "top_chapters": sorted(((c, v[0], v[1], round(100 * v[0] / v[1], 1)) for c, v in by_ch.items() if v[1] > 300),
                              key=lambda x: -x[3])[:30],
       "samples": {k: rng.sample(v, min(12, len(v))) for k, v in samples.items()}}
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res["by_tantra"], ensure_ascii=False, indent=1))
