import sys, json
from collections import defaultdict
src = open("/mnt2/kengo/ocr-ahs-tika1928/reuse2.py").read().split("REF = kset")[0]
sys.argv = ["x", "/dev/null"]; exec(src)
F = json.load(open("misfile3.json"))
bad = defaultdict(set)
for k, L in F.items():
    for v, raw in L: bad[k.split(">")[0]].add(raw)
T = {w: load("t1928", w) for w in ("candranandana", "arunadatta", "hemadri")}
su = {v[:2] for v in T["arunadatta"]}
Pp = {w: load("parad", w, su) for w in ("arunadatta", "hemadri")}
def clean(by, who):   # drop suspect sentences from a 1928 stream (B side)
    out = defaultdict(list)
    for v, raw, n in sentences(by):
        if raw not in bad[who]: out[v].append(raw)
    return out
TC = {w: clean(b, w) for w, b in T.items()}
def rate(A, B, who_A=None):
    S = sentences(A); win, _ = windows(B); d = defaultdict(lambda: [0, 0])
    for v, raw, n in S:
        if who_A and raw in bad[who_A]: continue
        s = fuzz.partial_ratio(n, win(v)) if win(v) else 0
        c = "%s.%d" % v[:2]; k = c if c in ("Sū.1", "Sū.6", "Sū.7", "Sū.30") else "other 26"
        for kk in (k, "ALL"):
            d[kk][1] += len(n); d[kk][0] += len(n) * (s >= 85)
    return {k: round(100 * a / b, 1) for k, (a, b) in d.items()}
for label, A, B, wa in [("ARp ← CN", Pp["arunadatta"], T["candranandana"], None), ("ARp ← CN clean", Pp["arunadatta"], TC["candranandana"], None),
                        ("AR28 ← CN", T["arunadatta"], T["candranandana"], None), ("AR28 clean ← CN clean", T["arunadatta"], TC["candranandana"], "arunadatta"),
                        ("HEp ← CN", Pp["hemadri"], T["candranandana"], None), ("HEp ← CN clean", Pp["hemadri"], TC["candranandana"], None),
                        ("HE28 ← CN", T["hemadri"], T["candranandana"], None), ("HE28 clean ← CN clean", T["hemadri"], TC["candranandana"], "hemadri")]:
    print(f"{label:24s}", rate(A, B, wa))
