#!/usr/bin/env python3
"""Anchor the Tibetan Vaiḍūryakabhāṣya (D4311) to root verses (D&E numbering).
The bhāṣya is a running paraphrase, so it is split into chapters by its own colophons (numbered within
each sthāna, reset at the sthāna-end colophons), and within each chapter overlapping windows of its text
are Viterbi-aligned (monotone, no band) to the chapter's verses with the Dharmamitra alignment embedder.
Usage: tib_d4311.py PAGES_DIR UNITS_JSON EMB_DIR OUT_JSON          (ocr env python, GPU)
"""
import glob, json, os, re, sys
from collections import Counter
import numpy as np

pages, units_f, emb_dir, out = sys.argv[1:5]
sys.path.insert(0, "/tmp/claude-1003/-mnt2-kengo-dharmamitra-claude-code-agent/9b933fb8-c99e-4510-8390-60566566cdf3/scratchpad/py")
import pyewts
conv = pyewts.pyewts()
syl = lambda t: len([x for x in re.split(r"[\s/]+", t) if x])
U = json.load(open(units_f))

def segs(fn):
    for p in sorted(glob.glob(f"{pages}/{fn}.*.json")):
        for it in json.load(open(p))["items"]:
            yield it["segnr"], "".join(x["text"] for x in it["segtext"]).strip()
T = list(segs("BO_T13_D4311")) + list(segs("BO_T13_D4311-2"))

# ---------------------------------------------------------------- chapters from numbered colophons
# The bhāṣya also closes sub-sections (e.g. of Sū.5, Sū.6) with unnumbered "… le'u rdzogs so"; only
# colophons carrying a chapter numeral mark chapter ends. Chapters without one merge into the next span.
U1 = ["", "gcig", "gnyis", "gsum", "bzhi", "lnga", "drug", "bdun", "brgyad", "dgu"]
NUM = {"dang po": 1, "bcu": 10, "nyi shu": 20, "sum cu": 30, "bzhi bcu": 40}
for i in range(2, 10): NUM[U1[i]] = i
for i in range(1, 10):
    NUM[("bco " if i in (5, 8) else "bcu ") + U1[i]] = 10 + i
    NUM["nyi shu rtsa " + U1[i]] = 20 + i; NUM["nyer " + U1[i]] = 20 + i
    NUM["sum cu rtsa " + U1[i]] = 30 + i; NUM["so " + U1[i]] = 30 + i
NUMRE = re.compile(r"le'u(?: ste)?(?:'i)? (" + "|".join(sorted(map(re.escape, NUM), key=len, reverse=True)) + r"|tha ma)\b")
STH_END = re.compile(r"seng ge sbas pa|gnas zhes bya ba'i le'u .* rdzogs te|gnas te gnas .* rdzogs")
NEXP = [("Sū", 30), ("Śā", 6), ("Ni", 16), ("Ci", 22), ("Ka", 6), ("U", 40)]
chap_spans, s_i, prev_end, prev_n, last_k = [], 0, 0, 0, -10
last_end = -10
for k, (_, t) in enumerate(T):
    sth, nexp = NEXP[min(s_i, 5)]
    if STH_END.search(t):
        if k - last_end <= 3: continue                # same sthāna-end colophon, continued
        if prev_n < nexp:                             # close the sthāna's last chapter(s)
            chap_spans.append(([f"{sth}.{c}" for c in range(prev_n + 1, nexp + 1)], prev_end, k + 1))
            prev_end = k + 1
        s_i, prev_n, last_end = s_i + 1, 0, k
        continue
    m = NUMRE.search(t) if re.search(r"rdzogs|pa'o|ba'o|po'o", t) else None
    if not m or k - last_k <= 3: continue
    n = nexp if m.group(1) == "tha ma" else NUM[m.group(1)]
    if n <= prev_n or n > nexp: continue              # out-of-order or impossible numeral: ignore
    chap_spans.append(([f"{sth}.{c}" for c in range(prev_n + 1, n + 1)], prev_end, k + 1))
    prev_end, prev_n, last_k = k + 1, n, k
covered = Counter(c.split(".")[0] for cs, _, _ in chap_spans for c in cs)
print("spans", len(chap_spans), "| merged spans", sum(len(cs) > 1 for cs, _, _ in chap_spans),
      "| chapters covered per sthāna", dict(covered), "| expected", dict(NEXP))

# ---------------------------------------------------------------- embed windows and align per chapter
import torch
from transformers import AutoModel, AutoTokenizer
M = "/mnt2/kengo/hf-cache/hub/models--buddhist-nlp--mitra-qwen35-2b-embedder-sentence-alignment/snapshots/71f1b42db4feb4a3b0bbb9c5912c8dad39db1d16"
tok = AutoTokenizer.from_pretrained(M); tok.padding_side = "left"
model = AutoModel.from_pretrained(M, dtype=torch.bfloat16, device_map="cuda:0").eval()
def embed(texts, bs=32):
    res = np.zeros((len(texts), 2048), dtype=np.float32)
    idx = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    with torch.no_grad():
        for b in range(0, len(idx), bs):
            ii = idx[b:b + bs]
            enc = tok([texts[i] for i in ii], padding=True, truncation=True, max_length=512, return_tensors="pt").to(model.device)
            res[ii] = torch.nn.functional.normalize(model(**enc).last_hidden_state[:, -1].float(), dim=-1).cpu().numpy()
    return res

# verse embeddings per chapter (Sanskrit, pāda units merged per verse)
def chapter_verses(c):
    z = np.load(f"{emb_dir}/{c}.npz"); Sk = z["skt"].astype(np.float32)
    vecs, refs = [], []
    for i, u in enumerate(U["skt"][c]):
        key = re.sub(r"[a-d]+$", "", u["ref"]) if u["ref"] else None
        if not key: continue
        if refs and refs[-1] == key: vecs[-1] = vecs[-1] + Sk[i]
        else: vecs.append(Sk[i].copy()); refs.append(key)
    V = np.stack(vecs); return V / np.linalg.norm(V, axis=1, keepdims=True), refs

WIN, STRIDE = 5, 3
units, report = [], []
for names, a, b in chap_spans:
    names = [c for c in names if c in U["skt"]]
    if not names: continue
    name = names[0] if len(names) == 1 else f"{names[0]}–{names[-1].split('.')[1]}"
    wins = [i for i in range(a, b, STRIDE)]
    if not wins: continue
    W = embed([conv.toUnicode(" ".join(t for _, t in T[i:min(i + WIN, b)])) for i in wins])
    parts = [chapter_verses(c) for c in names]
    V = np.concatenate([p_[0] for p_ in parts]); refs = [r for p_ in parts for r in p_[1]]
    sim = W @ V.T
    nW, nV = sim.shape
    f = np.full(nV, -1e9); f[0] = sim[0, 0]
    back = np.zeros((nW, nV), dtype=np.int32)
    for j in range(1, nW):
        bp, arg = f.copy(), np.arange(nV)
        for d in range(1, 6):
            sh = np.full(nV, -1e9); sh[d:] = f[:-d] - 0.02 * (d - 1)
            better = sh > bp; bp = np.where(better, sh, bp); arg = np.where(better, np.arange(nV) - d, arg)
        f = bp + sim[j]; back[j] = arg
    path = [int(np.argmax(f))]
    for j in range(nW - 1, 0, -1): path.append(int(back[j][path[-1]]))
    path = path[::-1]
    for j, (i, vi) in enumerate(zip(wins, path)):
        part = " ".join(t for _, t in T[i:min(i + STRIDE, b)]).strip()
        if syl(part) >= 4:
            units.append({"work": "D4311", "verse": refs[vi], "seg": T[i][0], "wylie": part, "cos": round(float(sim[j, vi]), 3)})
    report.append((name, nW, nV, round(float(np.mean([sim[j, v] for j, v in enumerate(path)])), 3), len(set(path))))
json.dump(units, open(out, "w"), ensure_ascii=False)
print("chapters aligned", len(report), "| mean path cos %.3f" % np.mean([r[3] for r in report]),
      "| verses reached", sum(r[4] for r in report), "| units", len(units))
print("weakest chapters:", sorted(report, key=lambda r: r[3])[:8])
