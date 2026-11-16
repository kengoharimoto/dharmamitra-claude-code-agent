#!/usr/bin/env python3
"""Blind check of a random sample of proofreading corrections.
Usage: blind.py N SEED OUT_JSON  -> items with the block crops, context, readings A/B in random order (key kept apart)."""
import json, glob, random, sys
N, seed, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
random.seed(seed)
crops = {}
for f in glob.glob("t1928/*/pages.json"):
    for r in json.load(open(f)):
        for b in r["blocks"]: crops[(r["page"], b["block"])] = (b["crops"], b["ocr"])
C = [json.loads(l) for f in sorted(glob.glob("t1928/corr_*.jsonl")) for l in open(f)]
C = [c for c in C if c["kind"] in ("ocr", "missing") and c["old"] != c["new"]]
S = random.sample(C, N)
items, key = [], []
for i, c in enumerate(S):
    cr, ocr = crops[(c["page"], c["block"])]
    k = ocr.index(c["old"]); ctx = ocr[max(0, k - 60):k] + "【…】" + ocr[k + len(c["old"]):k + len(c["old"]) + 60]
    ab = [c["old"], c["new"]]; random.shuffle(ab)
    items.append(dict(id=i, page=c["page"], block=c["block"], crops=cr, context=ctx, A=ab[0], B=ab[1]))
    key.append(dict(id=i, proposed="A" if ab[0] == c["new"] else "B", conf=c["conf"], kind=c["kind"]))
json.dump(items, open(out, "w"), ensure_ascii=False, indent=1)
json.dump(key, open(out.replace(".json", "_key.json"), "w"), ensure_ascii=False, indent=1)
print(len(items))
