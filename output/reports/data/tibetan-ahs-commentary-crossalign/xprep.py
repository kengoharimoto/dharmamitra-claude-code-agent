#!/usr/bin/env python3
"""Build verse-anchored text chunks for the cross-alignment of Tibetan and Sanskrit AHS commentaries.
Sanskrit: Aruṇadatta + Hemādri from parad (complete), Candranandana from t1928 (Sū. only), plus the
t1928 Aruṇadatta/Hemādri (Sū.) as a second witness. Tibetan: D4312 (Padārthacandrikā), D4311
(Vaiḍūryakabhāṣya). Chunks are ≤ ~700 chars (IAST) / ≤ ~120 syllables (Tibetan), cut at daṇḍa/shad.
Usage: xprep.py VERSE_ORDER_JSON OUT_JSON           (system python3 -P)
"""
import json, re, sys
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
sys.path.insert(0, "/tmp/claude-1003/-mnt2-kengo-dharmamitra-claude-code-agent/9b933fb8-c99e-4510-8390-60566566cdf3/scratchpad/py")
import pyewts

order_f, out = sys.argv[1:3]
P = "/mnt2/kengo/ocr-ahs-tika1928"
conv = pyewts.pyewts()
an = json.load(open(order_f))
order = {v["verse"]: i for i, v in enumerate(an["verses"])}
vkey = lambda r: re.sub(r"(ab|cd|ef|gh)$", "", r or "")

def chunks(text, maxlen, sep):
    parts, cur = [], ""
    for piece in re.split(f"(?<={sep})", text):
        if len(cur) + len(piece) > maxlen and cur:
            parts.append(cur.strip()); cur = ""
        cur += piece
    if cur.strip(): parts.append(cur.strip())
    return [p for p in parts if len(p) >= 40]

items = []
def add_skt(book, who, label):
    by = {}
    for l in open(f"{P}/etext/{book}_structure.jsonl"):
        s = json.loads(l)
        if s["type"] == "comm" and s.get("who") == who and vkey(s["ref"]) in order:
            by.setdefault(vkey(s["ref"]), []).append(s["text"])
    for v, ts in by.items():
        iast = transliterate(" ".join(ts), sanscript.DEVANAGARI, sanscript.IAST)
        for c in chunks(iast, 700, r"[|।॥]"):
            items.append({"side": "skt", "work": label, "verse": v, "vi": order[v], "text": c})
add_skt("parad", "arunadatta", "Aruṇadatta")
add_skt("parad", "hemadri", "Hemādri")
add_skt("t1928", "candranandana", "Candranandana")
add_skt("parad", "candranandana", "Candranandana (Parāḍkar)")
add_skt("t1928", "arunadatta", "Aruṇadatta (1928)")
add_skt("t1928", "hemadri", "Hemādri (1928)")

for work, f in (("D4312", "tib_d4312.json"), ("D4311", "tib_d4311.json")):
    by = {}
    for u in json.load(open(f"{P}/check/{f}")):
        if u["verse"] in order: by.setdefault(u["verse"], []).append(u["wylie"])
    for v, ts in by.items():
        for c in chunks(" ".join(ts), 600, r"/"):
            items.append({"side": "tib", "work": work, "verse": v, "vi": order[v], "text": conv.toUnicode(c), "wylie": c})
json.dump(items, open(out, "w"), ensure_ascii=False)
from collections import Counter
print(Counter((i["side"], i["work"]) for i in items))
