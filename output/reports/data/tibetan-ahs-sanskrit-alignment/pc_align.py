# Align the Sanskrit Padārthacandrikā (OCR blocks, Sūtrasthāna) with the Tibetan D4312 blocks as one
# monotone sequence. Beads: a Sanskrit blocks <-> b Tibetan blocks (a, b in 1..3), or a block on either
# side left unmatched. Score per bead: w(a,b) * (cos - LAM - DELTA*(a+b-2)), w = (a+b)/2.
# usage: pc_align.py PC_SKT_JSON PC_TIB_JSON OUT_JSON [LAM]
import json, os, sys
import numpy as np, torch
from transformers import AutoModel, AutoTokenizer

skt_f, tib_f, out = sys.argv[1:4]
LAM = float(sys.argv[4]) if len(sys.argv) > 4 else 0.6
DELTA, K = 0.02, 3
M = "/mnt2/kengo/hf-cache/hub/models--buddhist-nlp--mitra-qwen35-2b-embedder-sentence-alignment/snapshots/71f1b42db4feb4a3b0bbb9c5912c8dad39db1d16"
sk = json.load(open(skt_f)); tb = json.load(open(tib_f))
cache = out.replace(".json", ".emb.npz")

if os.path.exists(cache):
    z = np.load(cache); ES, ET = z["ES"].astype(np.float32), z["ET"].astype(np.float32)
else:
    tok = AutoTokenizer.from_pretrained(M); tok.padding_side = "left"
    model = AutoModel.from_pretrained(M, dtype=torch.bfloat16, device_map="cuda:0").eval()
    def embed(texts, query, bs=16):
        if query: texts = [f"<instruct>Please find the semantically most similar text in Tibetan.\n<query>{t}" for t in texts]
        res = np.zeros((len(texts), 2048), dtype=np.float16)
        idx = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        with torch.no_grad():
            for b in range(0, len(idx), bs):
                ii = idx[b:b + bs]
                enc = tok([texts[i] for i in ii], padding=True, truncation=True, max_length=768, return_tensors="pt").to(model.device)
                res[ii] = torch.nn.functional.normalize(model(**enc).last_hidden_state[:, -1].float(), dim=-1).cpu().numpy().astype(np.float16)
        return res
    # merged runs of 1..K consecutive blocks: index i*K + (k-1)
    s_txt = [" ".join(x["iast"] for x in sk[i:i + k]) for i in range(len(sk)) for k in range(1, K + 1)]
    t_txt = [" ".join(x["uni"] for x in tb[j:j + k]) for j in range(len(tb)) for k in range(1, K + 1)]
    ES, ET = embed(s_txt, True), embed(t_txt, False)
    np.savez(cache, ES=ES, ET=ET)
    ES, ET = ES.astype(np.float32), ET.astype(np.float32)

n, m = len(sk), len(tb)
NEG = -1e9
f = np.full((n + 1, m + 1), NEG); f[0, 0] = 0; bp = {}
# band: monotone alignment of two sequences of similar order; restrict |i/n - j/m| <= 0.08
band = 0.08
for i in range(n + 1):
    lo, hi = max(0, int((i / n - band) * m)), min(m, int((i / n + band) * m) + 1)
    for j in range(lo, hi + 1):
        v = f[i, j]
        if v <= NEG / 2: continue
        if i < n and v > f[i + 1, j]: f[i + 1, j] = v; bp[(i + 1, j)] = (i, j, 1, 0)
        if j < m and v > f[i, j + 1]: f[i, j + 1] = v; bp[(i, j + 1)] = (i, j, 0, 1)
        for a in range(1, K + 1):
            if i + a > n: break
            for b in range(1, K + 1):
                if j + b > m: break
                if a > 1 and b > 1: continue                      # 1:b or a:1 only
                c = float(ES[i * K + a - 1] @ ET[j * K + b - 1])
                w = v + (a + b) / 2 * (c - LAM - DELTA * (a + b - 2))
                if w > f[i + a, j + b]: f[i + a, j + b] = w; bp[(i + a, j + b)] = (i, j, a, b, c)
beads, (i, j) = [], (n, m)
while (i, j) != (0, 0):
    e = bp[(i, j)]; pi, pj, a, b = e[:4]
    beads.append({"skt": list(range(pi, pi + a)), "tib": list(range(pj, pj + b)), "cos": e[4] if len(e) > 4 else None})
    i, j = pi, pj
beads = beads[::-1]
json.dump({"lam": LAM, "beads": beads}, open(out, "w"))
print("beads", len(beads), "| matched", sum(1 for b in beads if b["skt"] and b["tib"]),
      "| skt unmatched", sum(len(b["skt"]) for b in beads if not b["tib"]), "| tib unmatched", sum(len(b["tib"]) for b in beads if not b["skt"]))
