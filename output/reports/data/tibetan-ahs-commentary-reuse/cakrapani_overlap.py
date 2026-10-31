import sys, json, glob
src = open("/mnt2/kengo/ocr-ahs-tika1928/reuse2.py").read().split("REF = kset")[0]
sys.argv = ["x", "/dev/null"]; exec(src)
K=20
n = norm(open(glob.glob("/mnt2/kengo/E-texts/1_sanskr/6_sastra/7_ayur/cakrapani_*ocr.txt")[0]).read()); C = {hash(n[i:i+K]) for i in range(len(n)-K+1)}
S=[json.loads(l) for l in open("/mnt2/kengo/ocr-ahs-tika1928/etext/t1928_structure.jsonl")]
tot=0
for x in S:
    if x.get("who")!="arunadatta": continue
    a=norm(transliterate(x["text"],sanscript.DEVANAGARI,sanscript.IAST))
    hit=sum(1 for i in range(0,len(a)-K+1,5) if hash(a[i:i+K]) in C)*5
    if hit>200: tot+=hit; print(x["ref"],x["page"],len(a),hit,"|",x["text"][:70],"…",x["text"][-50:])
print(tot)
