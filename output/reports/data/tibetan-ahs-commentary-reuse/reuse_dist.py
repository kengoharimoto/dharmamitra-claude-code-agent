import sys, re, random
src = open("/mnt2/kengo/ocr-ahs-tika1928/reuse2.py").read()
src = src.split("CN, AR, HE = ")[0]   # definitions only
sys.argv = ["x", "/dev/null"]; exec(src)
import numpy as np
def dist(A, B, win_override=None):
    global WIN
    old = WIN
    if win_override: WIN = win_override
    S = sentences(A); win, chB = windows(B); chapters = list(chB)
    real, nul = [], []
    for v, raw, n in S:
        w = win(v); real.append((fuzz.partial_ratio(n, w) if w else 0, len(n)))
        c = random.choice([c for c in chapters if c != v[:2]]); u = random.choice(chB[c])
        wn = win((c[0], c[1], u[2])); nul.append((fuzz.partial_ratio(n, wn) if wn else 0, len(n)))
    WIN = old
    L = sum(l for _, l in real)
    return [(t, round(100*sum(l for s,l in real if s>=t)/L,1), round(100*sum(l for s,l in nul if s>=t)/L,1)) for t in (65,70,75,80,85,90,95)]
CN, AR, HE = (load("t1928", w) for w in ("candranandana", "arunadatta", "hemadri"))
print("AR<-CN Sū (threshold, real %, null %):", dist(AR, CN))
print("CN<-AR Sū:", dist(CN, AR))
print("HE<-CN Sū:", dist(HE, CN))
print("HE<-AR Sū:", dist(HE, AR))
hch = {v[:2] for v in load("parad", "hemadri") if v[0] != "Sū"}
AR2, HE2 = load("parad", "arunadatta", hch), load("parad", "hemadri", hch)
print("HE<-AR Ni/Ci/Ka whole chapter:", dist(HE2, AR2, 400))
