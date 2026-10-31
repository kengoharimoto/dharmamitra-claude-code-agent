import sys, json, re
src = open("/mnt2/kengo/ocr-ahs-tika1928/reuse2.py").read().split("REF = kset")[0]
sys.argv = ["x", "/dev/null"]; exec(src)
T = {w: load("t1928", w) for w in ("candranandana", "arunadatta", "hemadri")}
su = {v[:2] for v in T["arunadatta"]}
Pp = {w: load("parad", w, su) for w in ("arunadatta", "hemadri")}
W28 = {w: windows(b)[0] for w, b in T.items()}; Wp = {w: windows(b)[0] for w, b in Pp.items()}
sc = lambda n, w: fuzz.partial_ratio(n, w) if w else 0
S = [json.loads(l) for l in open("/mnt2/kengo/ocr-ahs-tika1928/etext/t1928_structure.jsonl")]
flag = {}
for who, other in (("candranandana", "hemadri"), ("candranandana", "arunadatta"), ("hemadri", "arunadatta"), ("arunadatta", "hemadri")):
    n_ = 0
    for v, raw, n in sentences(T[who]):
        o, me = sc(n, Wp[other](v)), (sc(n, Wp[who](v)) if who in Wp else 0)
        if o >= 90 and me < 75 and sc(n, W28[other](v)) < 85:
            flag.setdefault((who, other), []).append(("%s.%d.%d" % v, raw)); n_ += len(n)
    print(who, "→ really", other, "letters", n_, "passages", len(flag.get((who, other), [])))
json.dump({f"{a}>{b}": v for (a, b), v in flag.items()}, open("misfile3.json", "w"), ensure_ascii=False, indent=1)
# context for a sample
import random; random.seed(5)
for (a, b), L in flag.items():
    print("=====", a, "text that is really", b)
    for v, raw in random.sample(L, min(4, len(L))):
        key = raw[:25]
        for x in S:
            if x.get("who") == a and key in transliterate(x["text"], sanscript.DEVANAGARI, sanscript.IAST):
                t = transliterate(x["text"], sanscript.DEVANAGARI, sanscript.IAST); k = t.find(key)
                print(f"  [{v} p{x['page']} seg-len {len(t)} at {k}] …{t[max(0,k-160):k]} ⟦{t[k:k+80]}⟧"); break
