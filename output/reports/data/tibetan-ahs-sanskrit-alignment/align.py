# Monotone verse-to-span alignment of the Sanskrit AHS and D4310, chapter by chapter.
# Beads: 1 or 2 Sanskrit verses <-> 1..L Tibetan lines (score n_skt * (cos - LAM)); a Sanskrit verse
# left out (0); a Tibetan line left out (-MU; free for colophon / title lines).
# usage: align.py UNITS_JSON EMB_DIR OUT_JSON [LAM] [MU] [DELTA]
import json, os, sys
import numpy as np

units_f, emb, out = sys.argv[1:4]
LAM = float(sys.argv[4]) if len(sys.argv) > 4 else 0.75
MU = float(sys.argv[5]) if len(sys.argv) > 5 else 0.02
DELTA = float(sys.argv[6]) if len(sys.argv) > 6 else 0.03   # a 2-verse merge must beat separate beads by this per verse
d = json.load(open(units_f))
NEG = -1e9

def align_chapter(c):
    z = np.load(f"{emb}/{c}.npz")
    S, P, Sp = (z[k].astype(np.float32) for k in ("skt", "pairs", "spans"))
    m, L = int(z["m"]), int(z["L"])
    n = len(S)
    s1 = (S @ Sp.T).reshape(n, m, L)                              # s1[i, j, k-1]: verse i vs lines j..j+k-1
    s2 = (P @ Sp.T).reshape(max(0, n - 1), m, L) if n > 1 else None
    free = np.array([x["colophon"] or j < 6 and c == "Sū.1" for j, x in enumerate(d["tib"][c])])
    ins = np.where(free, 0.0, -MU)
    f = np.full((n + 1, m + 1), NEG); f[0, 0] = 0.0
    bp = {}
    for i in range(n + 1):
        for j in range(m + 1):
            v = f[i, j]
            if v <= NEG / 2: continue
            if i < n and v > f[i + 1, j]:                          # Sanskrit verse without Tibetan
                f[i + 1, j] = v; bp[(i + 1, j)] = (i, j, 1, 0)
            if j < m and v + ins[j] > f[i, j + 1]:                  # Tibetan line without Sanskrit
                f[i, j + 1] = v + ins[j]; bp[(i, j + 1)] = (i, j, 0, 1)
            if i < n:
                for k in range(1, min(L, m - j) + 1):
                    w = v + (s1[i, j, k - 1] - LAM)
                    if w > f[i + 1, j + k]: f[i + 1, j + k] = w; bp[(i + 1, j + k)] = (i, j, 1, k)
            if i + 1 < n:
                for k in range(2, min(L, m - j) + 1):
                    w = v + 2 * (s2[i, j, k - 1] - LAM - DELTA)
                    if w > f[i + 2, j + k]: f[i + 2, j + k] = w; bp[(i + 2, j + k)] = (i, j, 2, k)
    beads, (i, j) = [], (n, m)
    while (i, j) != (0, 0):
        pi, pj, a, b = bp[(i, j)]
        cos = None
        if a == 1 and b: cos = float(s1[pi, pj, b - 1])
        if a == 2: cos = float(s2[pi, pj, b - 1])
        beads.append({"skt": list(range(pi, pi + a)), "tib": list(range(pj, pj + b)), "cos": cos})
        i, j = pi, pj
    return beads[::-1]

res = {}
for c in d["order"]:
    if not os.path.exists(f"{emb}/{c}.npz"): continue
    res[c] = align_chapter(c)
json.dump({"lam": LAM, "mu": MU, "delta": DELTA, "chapters": res}, open(out, "w"))
print("aligned chapters:", len(res))
