#!/usr/bin/env python3
"""Anchor the Tibetan Padārthacandrikā (D4312, all three volumes) to root verses (D&E numbering).
Each block = lemma (verse lines quoted from the root) + "zhes bya ba la" + gloss. The lemma is located
in D4310 by fuzzy matching in a forward-moving window (D4312 often abridges or re-breaks the lines);
the D4310 line gives the verse via the D4310↔Sanskrit alignment.
Usage: tib_d4312.py PAGES_DIR ROOT_ANALYSIS_JSON UNITS_JSON OUT_JSON      (CPU; system python3 -P)
"""
import bisect, glob, json, re, sys
from rapidfuzz import fuzz

pages, analysis_f, units_f, out = sys.argv[1:5]
syl = lambda t: len([x for x in re.split(r"[\s/]+", t) if x])
nrm = lambda t: re.sub(r"[^a-z]", "", t.lower().replace("'", "q"))

def segs(fn):
    for p in sorted(glob.glob(f"{pages}/{fn}.*.json")):
        for it in json.load(open(p))["items"]:
            yield it["segnr"], "".join(x["text"] for x in it["segtext"]).strip()

an = json.load(open(analysis_f)); U = json.load(open(units_f))
seg2verse = {s: v["verse"] for v in an["verses"] for s in v["tib_segs"]}
lines = [(x["seg"], nrm(x["wylie"])) for c in U["order"] for x in U["tib"][c]]
big, starts = "", []
for _, t in lines:
    starts.append(len(big)); big += t
line_at = lambda pos: bisect.bisect_right(starts, pos) - 1
verse_of_line = []
last = None
for s, _ in lines:                                   # colophon lines inherit the preceding verse
    last = seg2verse.get(s, last); verse_of_line.append(last)

S = [x for fn in ("BO_T13_D4312", "BO_T13_D4312-2", "BO_T13_D4312-3") for x in segs(fn)]
ZBL = re.compile(r"zhes bya ba (la|ni)\s*/?\s*$")
is_verse = lambda t: syl(t) <= 12 and t.rstrip().endswith("/ /")
blocks, cur = [], {"lemma": [], "expl": []}
for seg, t in S:
    if ZBL.search(t):
        lem = []
        while cur["expl"] and is_verse(cur["expl"][-1][1]): lem.insert(0, cur["expl"].pop())
        blocks.append(cur); cur = {"lemma": lem, "expl": []}
    else:
        cur["expl"].append((seg, t))
blocks.append(cur)

units, ptr, last_v, n_anch, scores = [], 0, None, 0, []
for b in blocks:
    lem = nrm(" ".join(t for _, t in b["lemma"]))
    if len(lem) >= 12:
        for W in (3000, 12000, 40000):               # nearest acceptable occurrence first
            lo = max(0, starts[max(0, ptr - 30)])
            al = fuzz.partial_ratio_alignment(lem, big[lo:lo + W], score_cutoff=78)
            if al:
                k = line_at(lo + al.dest_start); ptr = k
                if verse_of_line[k]: last_v = verse_of_line[k]; n_anch += 1; scores.append(al.score)
                break
    expl = " ".join(t for _, t in b["expl"]).strip()
    if syl(expl) >= 4 and last_v:
        units.append({"work": "D4312", "verse": last_v, "seg": b["expl"][0][0], "lemma": " ".join(t for _, t in b["lemma"]),
                      "wylie": expl})
json.dump(units, open(out, "w"), ensure_ascii=False)
from collections import Counter
sth = Counter(u["verse"].split(".")[0] for u in units)
print(f"D4312 blocks {len(blocks)} | lemma anchored {n_anch} (median score {sorted(scores)[len(scores)//2] if scores else 0}) "
      f"| units {len(units)} | by sthāna {dict(sth)} | distinct verses {len({u['verse'] for u in units})}")
