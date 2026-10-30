# Which Sanskrit readings does the Tibetan presuppose? For each substantive pāda variant in the
# Das & Emmerick apparatus (\var), substitute it into the verse, embed, and compare with the aligned
# Tibetan span. Also test lines that other editions add (+n) against unaligned Tibetan runs.
# usage: variants.py SKT_TXT UNITS_JSON ALIGN_JSON ANALYSIS_JSON EMB_DIR OUT_JSON
import difflib, json, re, sys
import numpy as np, torch
from transformers import AutoModel, AutoTokenizer

skt_f, units_f, align_f, an_f, emb, out = sys.argv[1:7]
M = "/mnt2/kengo/hf-cache/hub/models--buddhist-nlp--mitra-qwen35-2b-embedder-sentence-alignment/snapshots/71f1b42db4feb4a3b0bbb9c5912c8dad39db1d16"
STH = {"sūtrasthāna": "Sū", "śārīrasthāna": "Śā", "nidānasthāna": "Ni", "cikitsāsthāna": "Ci", "kalpasthāna": "Ka", "uttarasthāna": "U"}
d = json.load(open(units_f)); A = json.load(open(align_f))["chapters"]; an = json.load(open(an_f))

# --- parse apparatus entries, tagged with the current chapter
entries, chap = [], None
ENT = re.compile(r"(\d+)\.(\d+(?:\.\d+)?)(\+\(?\d+\)?)?(™)?([a-f])([vc])\s+(.+?)(?=\s+\d+\.\d+(?:\.\d+)?(?:\+\(?\d+\)?)?™?[a-f][vc]\s|\s*$)")
blocks, cur = [], None                                  # \var{...} blocks, which may span several lines
for line in open(skt_f, encoding="utf-8-sig"):
    s = line.strip()
    if cur is not None:
        cur[1] += " " + s
        if "}" in s: blocks.append(tuple(cur)); cur = None
        continue
    m = re.match(r"^(\S+sthāna) (\d+)\s*$", s)
    if m and m.group(1) in STH: chap = f"{STH[m.group(1)]}.{m.group(2)}"; continue
    if "\\var{" in s and chap:
        body = s[s.index("\\var{") + 5:]
        if "}" in body: blocks.append((chap, body))
        else: cur = [chap, body]
for chap, body in blocks:
    body = body.split("}")[0].strip()
    for e in ENT.finditer(body):
        ch, vs, add, tm, pada, kind, txt = e.groups()
        if kind != "v" or ch != chap.split(".")[1]: continue
        entries.append({"chapter": chap, "verse": f"{chap}.{vs}{'*' if tm else ''}", "pada": pada, "added": bool(add),
                        "text": re.sub(r"\s+", " ", txt).strip()})

# --- locate units and their aligned spans
unit_ix = {}
for c in d["order"]:
    for i, u in enumerate(d["skt"][c]):
        if u["ref"]: unit_ix[u["ref"]] = (c, i)
bead_of = {}
for c, beads in A.items():
    for b in beads:
        if len(b["skt"]) == 1 and b["tib"]: bead_of[(c, b["skt"][0])] = (b["tib"][0], len(b["tib"]))

def substitute(verse, pada, var):
    halves = verse.split(" | ")
    h = 0 if pada in "ab" or len(halves) == 1 else 1
    half = halves[h]; words = half.split()
    best = (0, None)
    for a in range(len(words)):
        for b in range(a + 1, len(words) + 1):
            cand = " ".join(words[a:b])
            if not 0.6 <= len(cand) / max(1, len(var)) <= 1.6: continue
            r = difflib.SequenceMatcher(None, cand, var).ratio()
            if r > best[0]: best = (r, (a, b))
    if not best[1]: return None, None, 0
    a, b = best[1]
    base_p = " ".join(words[a:b])
    halves[h] = " ".join(words[:a] + [var] + words[b:])
    return " | ".join(halves), base_p, best[0]

tests = []
for e in entries:
    if e["added"]: continue
    key = e["verse"] if e["verse"] in unit_ix else e["verse"] + e["pada"] if e["verse"] + e["pada"] in unit_ix else None
    if not key: continue
    c, i = unit_ix[key]
    if (c, i) not in bead_of: continue
    base = d["skt"][c][i]["text"]
    if key.endswith(e["pada"]):                       # pāda-numbered unit: the unit is the pāda
        new, base_p, r = e["text"], base, difflib.SequenceMatcher(None, base, e["text"]).ratio()
    else:
        new, base_p, r = substitute(base, e["pada"], e["text"])
    if not new or r < 0.3: continue
    tests.append({**e, "unit": key, "c": c, "i": i, "base_pada": base_p, "ratio": round(r, 2), "var_verse": new})
subst = [t for t in tests if t["ratio"] < 0.75]       # lexically substantive variants only
print("apparatus entries", len(entries), "| testable", len(tests), "| substantive", len(subst))

tok = AutoTokenizer.from_pretrained(M); tok.padding_side = "left"
model = AutoModel.from_pretrained(M, dtype=torch.bfloat16, device_map="cuda:0").eval()
def embed(texts, query=True, bs=64):
    if query: texts = [f"<instruct>Please find the semantically most similar text in Tibetan.\n<query>{t}" for t in texts]
    outv = []
    with torch.no_grad():
        for b in range(0, len(texts), bs):
            enc = tok(texts[b:b + bs], padding=True, truncation=True, max_length=384, return_tensors="pt").to(model.device)
            outv.append(torch.nn.functional.normalize(model(**enc).last_hidden_state[:, -1].float(), dim=-1).cpu().numpy())
    return np.concatenate(outv) if outv else np.zeros((0, 2048))

V = embed([t["var_verse"] for t in subst])
cache = {}
for t, v in zip(subst, V):
    c, i = t["c"], t["i"]
    if c not in cache:
        z = np.load(f"{emb}/{c}.npz"); cache[c] = (z["skt"].astype(np.float32), z["spans"].astype(np.float32), int(z["L"]))
    S, Sp, L = cache[c]
    j, k = bead_of[(c, i)]
    span = Sp[j * L + k - 1]
    t["cos_base"] = round(float(S[i] @ span), 4); t["cos_var"] = round(float(v @ span), 4)
    t["delta"] = round(t["cos_var"] - t["cos_base"], 4)
    t["tib"] = " / ".join(d["tib"][c][x]["wylie"].rstrip("/ ") for x in range(j, j + k))
    t["verdict"] = "variant" if t["delta"] >= 0.02 else "base" if t["delta"] <= -0.02 else "undecided"

# --- added lines vs Tibetan plus runs
added = [e for e in entries if e["added"]]
AV = embed([e["text"] for e in added])
plus_by_c = {}
for p in an["plus_runs"]: plus_by_c.setdefault(p["chapter"], []).append(p)
add_hits = []
for e, v in zip(added, AV):
    c = e["chapter"]
    if c not in plus_by_c: continue
    if c not in cache:
        z = np.load(f"{emb}/{c}.npz"); cache[c] = (z["skt"].astype(np.float32), z["spans"].astype(np.float32), int(z["L"]))
    S, Sp, L = cache[c]
    best = (0, None)
    for p in plus_by_c[c]:
        for a in range(len(p["tib_idx"])):
            for k in range(1, min(L, len(p["tib_idx"]) - a) + 1):
                j = p["tib_idx"][a]; s = float(v @ Sp[j * L + k - 1])
                if s > best[0]: best = (s, (p, a, k))
    if best[0] >= 0.80:
        p, a, k = best[1]
        add_hits.append({"chapter": c, "added_after": e["verse"], "pada": e["pada"], "skt": e["text"], "cos": round(best[0], 3),
                         "segs": p["segs"][a:a + k], "tib": " / ".join(p["text"].split(" / ")[a:a + k])})

from collections import Counter
json.dump({"n_entries": len(entries), "n_testable": len(tests), "n_substantive": len(subst),
           "verdicts": Counter(t["verdict"] for t in subst), "tests": sorted(subst, key=lambda t: -abs(t["delta"])),
           "added_lines": len(added), "added_line_hits": sorted(add_hits, key=lambda h: -h["cos"])},
          open(out, "w"), ensure_ascii=False, indent=1)
print("verdicts", Counter(t["verdict"] for t in subst), "| added lines", len(added), "matched to Tibetan pluses", len(add_hits))
