# Segment the Tibetan Padārthacandrikā (D4312 vol. ko = Sū.1–29, plus Sū.30 from vol. kho) into
# commentary blocks: lemma (verse lines) + "zhes bya ba la" + explanation, with chapter labels.
# usage: pc_tib.py PAGES_DIR OUT_JSON [KHO_LAST_SEG]
import glob, json, re, sys
sys.path.insert(0, sys.argv[0].rsplit("/align/", 1)[0] + "/py")
import pyewts

pages, out = sys.argv[1:3]
kho_last = sys.argv[3] if len(sys.argv) > 3 else None
conv = pyewts.pyewts()

def segs(fn):
    for p in sorted(glob.glob(f"{pages}/{fn}.*.json")):
        for it in json.load(open(p))["items"]:
            yield it["segnr"], "".join(x["text"] for x in it["segtext"]).strip()

S = list(segs("BO_T13_D4312"))
if kho_last:                                             # Sū.30 = start of vol. kho up to its colophon
    for s in segs("BO_T13_D4312-2"):
        S.append(s)
        if s[0] == kho_last: break
syl = lambda t: len([x for x in re.split(r"[\s/]+", t) if x])
COLO = re.compile(r"le'u .*('grel (pa|ba)|bshad pa)'o")
ZBL = re.compile(r"^zhes bya ba (la|ni)\s*/?\s*$|zhes bya ba la\s*/\s*$")

blocks, ch = [], 1
i = 0
cur = None
def is_verse(t): return syl(t) <= 12 and t.rstrip().endswith("/ /")
while i < len(S):
    seg, t = S[i]
    ctx = " ".join(x for _, x in S[max(0, i - 2):i + 1])
    if COLO.search(t) and "zla ba la dga'" in ctx:
        if cur: blocks.append(cur); cur = None
        ch += 1; i += 1; continue
    if ZBL.search(t):
        # lemma = run of verse lines immediately before; they were appended to the previous block's
        # explanation, so take them back
        lem = []
        if cur:
            while cur["expl"] and is_verse(cur["expl"][-1][1]): lem.insert(0, cur["expl"].pop())
            blocks.append(cur)
        cur = {"chapter": f"Sū.{ch}", "lemma": lem, "expl": []}
        i += 1; continue
    if cur is None: cur = {"chapter": f"Sū.{ch}", "lemma": [], "expl": []}
    cur["expl"].append((seg, t)); i += 1
if cur: blocks.append(cur)

res = []
for b in blocks:
    expl = " ".join(t for _, t in b["expl"]).strip()
    if syl(expl) < 4: continue
    res.append({"chapter": b["chapter"], "segs": [s for s, _ in b["lemma"] + b["expl"]],
                "lemma": " ".join(t for _, t in b["lemma"]), "expl": expl, "uni": conv.toUnicode(expl), "syl": syl(expl)})
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
from collections import Counter
print("chapters:", ch - 1, "| blocks:", len(res), dict(sorted(Counter(r["chapter"] for r in res).items(), key=lambda x: int(x[0].split(".")[1]))))
