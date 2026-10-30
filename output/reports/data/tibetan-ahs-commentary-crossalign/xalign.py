#!/usr/bin/env python3
"""Cross-alignment: every Tibetan AHS commentary against every Sanskrit one, verse-anchored.
For a Tibetan chunk t at verse v and a Sanskrit work S:
  true(t,S)  = max cos(t, s) over S-chunks at verses v-1..v+1
  base(t,S)  = max cos(t, s) over S-chunks at verses v+6..v+8 (else v-8..v-6), same sthāna
Reports per (Tibetan work, Sanskrit work, sthāna): coverage, median true/base, share of chunks with a
clear match (true ≥ T_HIT and true - base ≥ MARGIN), and per chunk which Sanskrit work matches best.
Usage: xalign.py CHUNKS_JSON OUT_JSON            (ocr env python, GPU)
"""
import json, os, sys
from collections import defaultdict, Counter
import numpy as np, torch
from transformers import AutoModel, AutoTokenizer

chunks_f, out = sys.argv[1:3]
T_HIT, MARGIN = 0.84, 0.05
M = "/mnt2/kengo/hf-cache/hub/models--buddhist-nlp--mitra-qwen35-2b-embedder-sentence-alignment/snapshots/71f1b42db4feb4a3b0bbb9c5912c8dad39db1d16"
items = json.load(open(chunks_f))
cache = out.replace(".json", ".emb.npy")
if os.path.exists(cache):
    E = np.load(cache).astype(np.float32)
else:
    tok = AutoTokenizer.from_pretrained(M); tok.padding_side = "left"
    model = AutoModel.from_pretrained(M, dtype=torch.bfloat16, device_map="cuda:0").eval()
    texts = [(f"<instruct>Please find the semantically most similar text in Tibetan.\n<query>{i['text']}" if i["side"] == "skt" else i["text"]) for i in items]
    E = np.zeros((len(texts), 2048), dtype=np.float16)
    idx = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    with torch.no_grad():
        for b in range(0, len(idx), 24):
            ii = idx[b:b + 24]
            enc = tok([texts[i] for i in ii], padding=True, truncation=True, max_length=640, return_tensors="pt").to(model.device)
            E[ii] = torch.nn.functional.normalize(model(**enc).last_hidden_state[:, -1].float(), dim=-1).cpu().numpy().astype(np.float16)
            if b % 4800 == 0: print(f"  embedded {b}/{len(texts)}", flush=True)
    np.save(cache, E); E = E.astype(np.float32)

sth = lambda v: v.split(".")[0]
skt_works = sorted({i["work"] for i in items if i["side"] == "skt"})
tib_works = sorted({i["work"] for i in items if i["side"] == "tib"})
by_work_vi = defaultdict(lambda: defaultdict(list))        # skt work -> verse index -> item indices
for k, i in enumerate(items):
    if i["side"] == "skt": by_work_vi[i["work"]][i["vi"]].append(k)
vi_sth = {i["vi"]: sth(i["verse"]) for i in items}

def best(k, work, vis):
    cand = [j for v in vis for j in by_work_vi[work].get(v, [])]
    if not cand: return None, None
    s = E[cand] @ E[k]
    a = int(np.argmax(s)); return float(s[a]), cand[a]

rows, stats = [], defaultdict(lambda: {"n": 0, "true": [], "base": [], "hit": 0})
for k, i in enumerate(items):
    if i["side"] != "tib": continue
    v = i["vi"]; rec = {"tib": i["work"], "verse": i["verse"], "wylie": i.get("wylie", "")[:400], "skt": {}}
    for w in skt_works:
        t, tj = best(k, w, [v - 1, v, v + 1])
        if t is None: continue
        shift = [x for x in (v + 6, v + 7, v + 8) if vi_sth.get(x) == sth(i["verse"])] or \
                [x for x in (v - 8, v - 7, v - 6) if vi_sth.get(x) == sth(i["verse"])]
        b, _ = best(k, w, shift)
        st = stats[(i["work"], w, sth(i["verse"]))]
        st["n"] += 1; st["true"].append(t)
        if b is not None: st["base"].append(b)
        hit = t >= T_HIT and (b is None or t - b >= MARGIN)
        st["hit"] += hit
        rec["skt"][w] = {"cos": round(t, 3), "base": round(b, 3) if b is not None else None, "hit": hit,
                         "skt_text": items[tj]["text"][:400]}
    if rec["skt"]:
        top = sorted(rec["skt"].items(), key=lambda x: -x[1]["cos"])
        rec["winner"] = top[0][0] if (len(top) == 1 or top[0][1]["cos"] - top[1][1]["cos"] >= 0.02) else "tie"
        rows.append(rec)

summary = []
for (tw, sw, s), st in sorted(stats.items()):
    summary.append({"tib": tw, "skt": sw, "sthana": s, "tib_chunks_with_skt_coverage": st["n"],
                    "median_true": round(float(np.median(st["true"])), 3),
                    "median_base": round(float(np.median(st["base"])), 3) if st["base"] else None,
                    "clear_match_pct": round(100 * st["hit"] / st["n"], 1)})
# head-to-head among the works covering the same chunk
h2h = defaultdict(Counter)
for r in rows:
    if len(r["skt"]) > 1: h2h[(r["tib"], sth(r["verse"]), "+".join(sorted(r["skt"])))][r["winner"]] += 1
json.dump({"T_HIT": T_HIT, "MARGIN": MARGIN, "summary": summary,
           "head_to_head": [{"tib": a, "sthana": b, "works": c, "wins": dict(v)} for (a, b, c), v in h2h.items()],
           "chunks": rows}, open(out, "w"), ensure_ascii=False, indent=0)
for s in summary: print(s)
