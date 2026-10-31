#!/usr/bin/env python3
"""Group the misfiling suspects (check/misfile_suspects_t1928.json) into clusters: runs of suspect sentences
inside one t1928 segment. For each cluster record the segment, the character span (Devanagari) and what
precedes it, so that the start can be checked on the page image.   Usage: python3 -P clusters.py OUT_JSON"""
import json, re, sys
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
P = "/mnt2/kengo/ocr-ahs-tika1928"
F = json.load(open(f"{P}/check/misfile_suspects_t1928.json"))
S = [json.loads(l) for l in open(f"{P}/etext/t1928_structure.jsonl")]
IA = [transliterate(s["text"], sanscript.DEVANAGARI, sanscript.IAST) for s in S]
VEND = re.compile(r"\|\|\s*[0-9]+(?:\s*[-–,]\s*[0-9]+)*\s*\|\|")
hits = []
for key, L in F.items():
    who, really = key.split(">")
    for v, raw in L:
        k = raw[:30]
        for i, s in enumerate(S):
            if s.get("who") == who and k in IA[i]:
                a = IA[i].find(k); hits.append((i, a, a + len(raw), who, really, v)); break
hits.sort()
cl = []
for h in hits:
    i, a, b, who, really, v = h
    if cl and cl[-1]["seg"] == i and cl[-1]["really"] == really and a - cl[-1]["end"] < 250:
        cl[-1]["end"] = max(cl[-1]["end"], b); cl[-1]["n"] += 1
    else:
        cl.append({"seg": i, "start": a, "end": b, "who": who, "really": really, "verse": v, "n": 1})
for c in cl:
    t = IA[c["seg"]]
    before = t[max(0, c["start"] - 120):c["start"]]
    c.update(page=S[c["seg"]]["page"], seglen=len(t), at_seg_start=c["start"] < 40,
             after_vend=bool(VEND.search(before[-40:])), letters=c["end"] - c["start"],
             before=before, text=t[c["start"]:c["end"]][:300])
json.dump(cl, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
from collections import Counter
print("suspect sentences located", len(hits), "| clusters", len(cl))
print(Counter((c["who"], c["really"]) for c in cl))
print("at segment start", sum(c["at_seg_start"] for c in cl), "| right after a verse-end ॥n॥", sum(c["after_vend"] for c in cl),
      "| single-sentence clusters", sum(c["n"] == 1 for c in cl), "| letters ≥ 300", sum(c["letters"] >= 300 for c in cl))
