# Embed Sanskrit verses (and adjacent-verse pairs) as queries, and every Tibetan span of 1..L lines
# within each chapter as targets, with the mitra sentence-alignment embedder.
# usage: embed.py UNITS_JSON OUT_DIR [L] [--bench N]
import json, os, sys, time
import numpy as np, torch
from transformers import AutoModel, AutoTokenizer

units_f, out = sys.argv[1], sys.argv[2]
L = int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else 8
bench = int(sys.argv[sys.argv.index("--bench") + 1]) if "--bench" in sys.argv else 0
M = "/mnt2/kengo/hf-cache/hub/models--buddhist-nlp--mitra-qwen35-2b-embedder-sentence-alignment/snapshots/71f1b42db4feb4a3b0bbb9c5912c8dad39db1d16"
tok = AutoTokenizer.from_pretrained(M); tok.padding_side = "left"
model = AutoModel.from_pretrained(M, dtype=torch.bfloat16, device_map="cuda:0").eval()

def embed(texts, query=False, bs=64):
    if query:
        texts = [f"<instruct>Please find the semantically most similar text in Tibetan.\n<query>{t}" for t in texts]
    idx = sorted(range(len(texts)), key=lambda i: len(texts[i]))      # length-bucketed batches
    res = np.zeros((len(texts), 2048), dtype=np.float16)
    with torch.no_grad():
        for b in range(0, len(idx), bs):
            ii = idx[b:b + bs]
            enc = tok([texts[i] for i in ii], padding=True, truncation=True, max_length=384, return_tensors="pt").to(model.device)
            h = model(**enc).last_hidden_state[:, -1]
            res[ii] = torch.nn.functional.normalize(h.float(), dim=-1).cpu().numpy().astype(np.float16)
    return res

d = json.load(open(units_f))
os.makedirs(out, exist_ok=True)
if bench:
    tib = [x["uni"] for c in d["order"] for x in d["tib"][c]][:bench]
    spans = [" ".join(tib[j:j + k]) for j in range(len(tib)) for k in (1, 4, 8)][:bench]
    t0 = time.time(); embed(spans); print(f"{len(spans)} spans in {time.time() - t0:.1f}s"); sys.exit()

only = sys.argv[sys.argv.index("--chapters") + 1].split(",") if "--chapters" in sys.argv else None
for c in d["order"]:
    if only and c not in only: continue
    f = f"{out}/{c}.npz"
    if os.path.exists(f): continue
    sk = [x["text"] for x in d["skt"][c]]
    pairs = [sk[i] + " | " + sk[i + 1] for i in range(len(sk) - 1)]
    tib = [x["uni"] for x in d["tib"][c]]
    spans = [" ".join(tib[j:j + k]) for j in range(len(tib)) for k in range(1, L + 1)]   # index j*L + (k-1)
    t0 = time.time()
    np.savez(f, skt=embed(sk, True), pairs=embed(pairs, True) if pairs else np.zeros((0, 2048), np.float16),
             spans=embed(spans), m=len(tib), L=L)
    print(c, len(sk), len(tib), f"{time.time() - t0:.0f}s", flush=True)
