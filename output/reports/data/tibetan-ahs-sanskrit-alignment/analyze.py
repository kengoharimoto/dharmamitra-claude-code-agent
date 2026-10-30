# Summarise the Sanskrit↔Tibetan alignment: per-verse status, Tibetan pluses, runs of omissions,
# and transpositions (a Sanskrit verse missing in place whose best match is an unaligned Tibetan run).
# usage: analyze.py UNITS_JSON ALIGN_JSON EMB_DIR OUT_JSON
import json, re, sys
from collections import Counter, defaultdict
import numpy as np

units_f, align_f, emb, out = sys.argv[1:5]
d = json.load(open(units_f)); A = json.load(open(align_f))["chapters"]
CLOSE, LOOSE = 0.85, 0.78
FORMULA = re.compile(r"le'u bshad par bya|'di ltar bshad do|zhes bya ba'i le'u|bshad par bya'o")
verse_of = lambda ref: re.sub(r"[a-z]+$", "", ref) if ref else None

rows, plus_runs, omit_runs, trans = [], [], [], []
tot = Counter()
for c, beads in A.items():
    skt, tib = d["skt"][c], d["tib"][c]
    st_unit = {}          # skt unit index -> (status, cos, tib idx list)
    tib_used = set()
    for b in beads:
        if b["skt"] and b["tib"]:
            s = "close" if b["cos"] >= CLOSE else "loose" if b["cos"] >= LOOSE else "doubtful"
            for i in b["skt"]: st_unit[i] = (s, b["cos"], b["tib"])
            tib_used.update(b["tib"])
        elif b["skt"]:
            for i in b["skt"]: st_unit[i] = ("absent", None, [])
    # Tibetan line classes
    tclass = []
    for j, x in enumerate(tib):
        if j in tib_used: tclass.append("aligned")
        elif x["colophon"] or (c == "Sū.1" and j < 6): tclass.append("colophon/title")
        elif FORMULA.search(x["wylie"]) and (j < 12 or j > len(tib) - 4): tclass.append("chapter formula")
        else: tclass.append("plus")
    for k in tclass: tot["tib " + k] += 1
    for j, k in enumerate(tclass): tot["tibsyl " + k] += tib[j]["syl"]
    # verse-level status (pāda units regrouped)
    by_v = defaultdict(list)
    for i, u in enumerate(skt): by_v[verse_of(u["ref"]) or f"{c}.prose{i}"].append(i)
    for v, ii in by_v.items():
        ss = [st_unit[i][0] for i in ii]
        status = ss[0] if len(set(ss)) == 1 else ("partial" if "absent" in ss else min(ss, key=["close", "loose", "doubtful"].index))
        cos = [st_unit[i][1] for i in ii if st_unit[i][1] is not None]
        tj = sorted({j for i in ii for j in st_unit[i][2]})
        rows.append({"chapter": c, "verse": v, "status": status, "cos": round(float(np.mean(cos)), 3) if cos else None,
                     "skt": " | ".join(skt[i]["text"] for i in ii),
                     "tib_segs": [tib[j]["seg"] for j in tj], "tib": " / ".join(tib[j]["wylie"].rstrip("/ ") for j in tj)})
        tot["verses"] += 1; tot["verse " + status] += 1
    # runs
    cur = []
    for j, k in enumerate(tclass + ["end"]):
        if k == "plus": cur.append(j)
        elif cur:
            plus_runs.append({"chapter": c, "tib_idx": cur, "segs": [tib[x]["seg"] for x in cur],
                              "text": " / ".join(tib[x]["wylie"].rstrip("/ ") for x in cur), "lines": len(cur)}); cur = []
    cur = []
    vs = [r for r in rows if r["chapter"] == c]
    for r in vs + [{"status": "end"}]:
        if r["status"] == "absent": cur.append(r)
        elif cur:
            omit_runs.append({"chapter": c, "verses": [x["verse"] for x in cur], "skt": [x["skt"] for x in cur]}); cur = []
    # transposition check: absent verses vs spans starting inside unaligned Tibetan runs
    z = np.load(f"{emb}/{c}.npz"); S = z["skt"].astype(np.float32); Sp = z["spans"].astype(np.float32); L = int(z["L"])
    free_js = [j for j, k in enumerate(tclass) if k == "plus"]
    for i, u in enumerate(skt):
        if st_unit[i][0] != "absent" or not free_js or len(u["text"]) < 50: continue
        best = (0, None, None)
        for j in free_js:
            for k in range(1, L + 1):
                if all(tclass[jj] == "plus" for jj in range(j, min(j + k, len(tib)))) and j + k <= len(tib):
                    s = float(S[i] @ Sp[j * L + k - 1])
                    if s > best[0]: best = (s, j, k)
        if best[0] >= CLOSE:
            j, k = best[1], best[2]
            trans.append({"chapter": c, "unit": u["ref"], "cos": round(best[0], 3), "segs": [tib[x]["seg"] for x in range(j, j + k)],
                          "skt": u["text"], "tib": " / ".join(tib[x]["wylie"].rstrip("/ ") for x in range(j, j + k))})

summary = dict(tot)
json.dump({"summary": summary, "verses": rows, "plus_runs": plus_runs, "omit_runs": omit_runs, "transpositions": trans},
          open(out, "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))
print("plus runs:", len(plus_runs), "(>=2 lines:", sum(p["lines"] >= 2 for p in plus_runs), ")  omission runs:", len(omit_runs),
      "  transpositions:", len(trans))
