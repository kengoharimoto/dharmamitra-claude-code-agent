# Build chapter-parallel unit lists for the Sanskrit AHS (Das & Emmerick e-text) and the Derge D4310.
# Sanskrit unit = one numbered verse (both half-lines); unnumbered prose is cut at sentence ends.
# Tibetan unit = one DharmaNexus segment (normally one pāda), Wylie + Unicode.
# usage: prep.py SKT_TXT PAGES_DIR OUT_JSON
import glob, json, re, sys
sys.path.insert(0, sys.argv[0].rsplit("/align/", 1)[0] + "/py")
import pyewts

skt_f, pages, out = sys.argv[1:4]
conv = pyewts.pyewts()
STH = {"sūtrasthāna": "Sū", "śārīrasthāna": "Śā", "nidānasthāna": "Ni", "cikitsāsthāna": "Ci", "kalpasthāna": "Ka", "uttarasthāna": "U"}

# --- Sanskrit
chap, skt, buf = None, {}, []
def flush(ref=None):
    global buf
    t = " ".join(buf).strip()
    if t and chap:
        skt.setdefault(chap, []).append({"ref": ref, "text": re.sub(r"\s+", " ", t)})
    buf = []
invar = False                                          # inside a multi-line \var{...} apparatus block
for line in open(skt_f, encoding="utf-8-sig"):
    s = line.strip()
    if invar:
        invar = "}" not in s
        continue
    if "\\var{" in s:
        invar = "}" not in s[s.index("\\var{"):]
        s = s[:s.index("\\var{")].strip()
    if not s or s.startswith("%"):
        continue
    m = re.match(r"^(\S+sthāna) (\d+)\s*$", s)
    if m and m.group(1) in STH:
        flush(); chap = f"{STH[m.group(1)]}.{m.group(2)}"; continue
    m = re.search(r"\|\|\s*([0-9]+(?:\.[0-9]+)?(?:™)?(?:\+\(?[0-9]+\)?)?[a-z]*)\s*\|\|\s*$", s)
    if m:
        buf.append(s[:m.start()].rstrip(" |")); flush(f"{chap}.{m.group(1).replace('™', '*')}")
    else:
        buf.append(s)
        if len(" ".join(buf)) > 600: flush()          # long unnumbered prose: cut
flush()

# --- Tibetan: chapter of each segment from the colophons (same rules as the census)
KEYS = [("phyi ma'i", "U"), ("cho ga grub pa'i", "Ka"), ("gso ba'i gnas", "Ci"), ("nad gzhi'i gnas", "Ni"),
        ("lus kyi gnas", "Śā"), ("mdo'i gnas", "Sū")]
COLO = re.compile(r"le'u (ste )?[^/]*?'o")
S10 = []
for p in sorted(glob.glob(f"{pages}/BO_T13_D4310.*.json")):
    for it in json.load(open(p))["items"]:
        S10.append((it["segnr"], "".join(x["text"] for x in it["segtext"]).strip()))
from collections import Counter
cnt, lab, iscolo = Counter(), [None] * len(S10), [False] * len(S10)
for k, (_, t) in enumerate(S10):
    if not COLO.search(t): continue
    ctx = (S10[k - 1][1] if k else "") + " " + t
    st = next((a for key, a in KEYS if key in t), None) or (next((a for key, a in KEYS if key in ctx), None) if "bsdus pa las" in ctx else None)
    if st:
        cnt[st] += 1; lab[k] = f"{st}.{cnt[st]}"; iscolo[k] = True
        if k and "bsdus pa las" in S10[k - 1][1]: iscolo[k - 1] = True
nxt = "U.40"
for k in range(len(S10) - 1, -1, -1):
    nxt = lab[k] or nxt; lab[k] = nxt
tib = {}
for k, ((segnr, t), c) in enumerate(zip(S10, lab)):
    w = re.sub(r"[@#]+", "", t).strip()
    if not re.search(r"[a-zA-Z]", w): continue
    tib.setdefault(c, []).append({"seg": segnr, "wylie": w, "uni": conv.toUnicode(w), "colophon": iscolo[k],
                                  "syl": len([x for x in re.split(r"[\s/]+", w) if x])})
order = [f"{a}.{i}" for a, n in [("Sū", 30), ("Śā", 6), ("Ni", 16), ("Ci", 22), ("Ka", 6), ("U", 40)] for i in range(1, n + 1)]
json.dump({"order": order, "skt": skt, "tib": tib}, open(out, "w"), ensure_ascii=False)
ns, nt = sum(len(v) for v in skt.values()), sum(len(v) for v in tib.values())
print("skt chapters", len(skt), "units", ns, "| tib chapters", len(tib), "units", nt, "syl", sum(x["syl"] for v in tib.values() for x in v))
ratios = sorted((len(tib.get(c, [])) / max(1, len(skt.get(c, []))), c, len(skt.get(c, [])), len(tib.get(c, []))) for c in order)
print("tib lines per skt verse: median", ratios[len(ratios)//2][0].__round__(2), "min", ratios[:3], "max", ratios[-3:])
