import sys, json
from collections import defaultdict
src = open("/mnt2/kengo/ocr-ahs-tika1928/reuse2.py").read().split("CN, AR, HE = ")[0]
sys.argv = ["x", "/dev/null"]; exec(src)
def perch(A, B):
    S = sentences(A); win, _ = windows(B); d = defaultdict(lambda: [0, 0])
    for v, raw, n in S:
        w = win(v); s = fuzz.partial_ratio(n, w) if w else 0
        k = "%s.%d" % v[:2]; d[k][1] += len(n)
        if s >= T_SHARED: d[k][0] += len(n)
    return {k: round(100 * a / b, 1) for k, (a, b) in d.items() if b > 1500}, round(100*sum(a for a,b in d.values())/sum(b for a,b in d.values()),1)
CN, AR, HE = (load("t1928", w) for w in ("candranandana", "arunadatta", "hemadri"))
su = {v[:2] for v in AR}
ARp, HEp = load("parad", "arunadatta", su), load("parad", "hemadri", su)
cols = {"AR28<-CN": perch(AR, CN), "ARpar<-CN": perch(ARp, CN), "AR28<-ARpar": perch(AR, ARp),
        "HE28<-CN": perch(HE, CN), "HEpar<-CN": perch(HEp, CN), "HE28<-HEpar": perch(HE, HEp),
        "CN<-AR28": perch(CN, AR), "CN<-ARpar": perch(CN, ARp)}
print("chapter " + " ".join(f"{k:>12s}" for k in cols))
for i in range(1, 31):
    k = f"Sū.{i}"; print(f"{k:7s} " + " ".join(f"{cols[c][0].get(k, float('nan')):12.1f}" for c in cols))
print("TOTAL   " + " ".join(f"{cols[c][1]:12.1f}" for c in cols))
json.dump({c: v[0] | {"TOTAL": v[1]} for c, v in cols.items()}, open("/mnt2/kengo/ocr-ahs-tika1928/check/reuse_perchapter.json", "w"), ensure_ascii=False, indent=1)
