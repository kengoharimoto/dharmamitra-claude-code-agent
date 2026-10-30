# For verses rendered in both D4310 (Rin chen bzang po) and D4311 (Gu ge bhāṣya), which rendering's
# distinctive wording does the Rgyud bzhi reproduce?
# usage: rendering_test.py PAIRS_JSON RGYUD_DIR OUT_JSON
import glob, json, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, sys.argv[0].rsplit("/bin/", 1)[0] + "/py")
import pyewts

pairs_f, rdir, out = sys.argv[1:4]
conv = pyewts.pyewts()

def syls(w):
    w = w.lower().replace("+", "")
    w = re.sub(r"[/|;:!@#*_\[\]()«»<>0-9\\-]+", " ", w)
    return [s for s in w.split() if s]
bg = lambda s: [tuple(s[i:i + 2]) for i in range(len(s) - 1)]

def wylie_file(b):
    return conv.toWylie(open(glob.glob(f"{rdir}/MonlamAI_{b}/*.txt")[0], encoding="utf-8").read())
rtsa = wylie_file("BO4623"); rtsa = rtsa[:rtsa.find("rtsa ba'i rgyud ces bya ba rdzogs") + 40]
R, Rlab = [], []
for name, w in [("Rtsa", rtsa), ("Bshad", wylie_file("BO2889")), ("Man ngag (1-27)", wylie_file("BO5092")), ("Phyi", wylie_file("BO5093"))]:
    ch = 1
    for chunk in re.split(r"(le'u ste [^/]*?pa'o)", w):
        for s in syls(chunk): R.append(s); Rlab.append(f"{name} ch.{ch}")
        if re.match(r"le'u ste [^/]*?pa'o", chunk): ch += 1
RB = bg(R)
freq = Counter(RB)
idx = defaultdict(list)
for i, b in enumerate(RB): idx[b].append(i)
STOP = {b for b, n in freq.items() if n > 50}

rows = json.load(open(pairs_f)); rows = rows if isinstance(rows, list) else rows.get("rows", rows)
res, tally = [], Counter()
for r in rows:
    a, p = syls(r["root_text"]), syls(r["par_text"])
    ba, bp = set(bg(a)) - STOP, set(bg(p)) - STOP
    if not ba: continue
    L = max(len(a), len(p))
    # candidate anchors: positions of any non-stop bigram of either rendering
    cand = Counter()
    for b in ba | bp:
        if len(idx[b]) <= 20:
            for j in idx[b]: cand[j // 8] += 1
    if not cand: tally["no rgyud match"] += 1; continue
    best = max(cand, key=cand.get) * 8
    win = set(RB[max(0, best - L - 8): best + L + 8])
    shared_ap = ba & bp
    da, dp = ba - bp, bp - ba
    hit_shared, hit_a, hit_p = len(shared_ap & win), len(da & win), len(dp & win)
    recall = len((ba | bp) & win) / len(ba | bp)
    if recall < float(sys.argv[4] if len(sys.argv) > 4 else 0.35): tally["weak rgyud match"] += 1; continue
    verdict = "D4310" if hit_a > hit_p else "D4311" if hit_p > hit_a else "tie"
    tally[verdict] += 1
    res.append({"root_segnr": r.get("root_segnr_range"), "par_segnr": r.get("par_segnr_range"), "score": r["score"],
                "rgyud": Rlab[best], "recall": round(recall, 2), "distinct_D4310_in_rgyud": hit_a,
                "distinct_D4311_in_rgyud": hit_p, "shared_in_rgyud": hit_shared, "verdict": verdict,
                "d4310": " ".join(a), "d4311": " ".join(p), "rgyud_text": " ".join(R[max(0, best - 4): best + L + 4])})
json.dump({"tally": tally, "pairs": sorted(res, key=lambda x: -x["recall"])}, open(out, "w"), ensure_ascii=False, indent=1)
print(dict(tally))
