# Recompute the Sanskrit-side embeddings (verses, adjacent pairs) for corrected units, reusing the
# Tibetan span embeddings already computed.  usage: embed_skt.py UNITS_JSON OLD_EMB_DIR NEW_EMB_DIR
import json, os, sys
import numpy as np, torch
from transformers import AutoModel, AutoTokenizer

units_f, old, new = sys.argv[1:4]
M = "/mnt2/kengo/hf-cache/hub/models--buddhist-nlp--mitra-qwen35-2b-embedder-sentence-alignment/snapshots/71f1b42db4feb4a3b0bbb9c5912c8dad39db1d16"
tok = AutoTokenizer.from_pretrained(M); tok.padding_side = "left"
model = AutoModel.from_pretrained(M, dtype=torch.bfloat16, device_map="cuda:0").eval()

def embed(texts, bs=64):
    texts = [f"<instruct>Please find the semantically most similar text in Tibetan.\n<query>{t}" for t in texts]
    res = np.zeros((len(texts), 2048), dtype=np.float16)
    idx = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    with torch.no_grad():
        for b in range(0, len(idx), bs):
            ii = idx[b:b + bs]
            enc = tok([texts[i] for i in ii], padding=True, truncation=True, max_length=384, return_tensors="pt").to(model.device)
            res[ii] = torch.nn.functional.normalize(model(**enc).last_hidden_state[:, -1].float(), dim=-1).cpu().numpy().astype(np.float16)
    return res

d = json.load(open(units_f)); os.makedirs(new, exist_ok=True)
for c in d["order"]:
    z = np.load(f"{old}/{c}.npz")
    assert int(z["m"]) == len(d["tib"][c]), c
    sk = [x["text"] for x in d["skt"][c]]
    pairs = [sk[i] + " | " + sk[i + 1] for i in range(len(sk) - 1)]
    np.savez(f"{new}/{c}.npz", skt=embed(sk), pairs=embed(pairs) if pairs else np.zeros((0, 2048), np.float16),
             spans=z["spans"], m=z["m"], L=z["L"])
print("done", len(d["order"]))
