# Extract the Padārthacandrikā (siglum प०) blocks from the OCR of the 1928 Sūtrasthāna edition
# (archive.org djvu.txt), by chapter, with the verse number each block ends on; transliterate to IAST.
# usage: pc_prep.py DJVU_TXT OUT_JSON
import json, re, sys
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

src, out = sys.argv[1:3]
DEV = re.compile(r"[ऀ-ॿ]")
DIG = str.maketrans("०१२३४५६७८९", "0123456789")
SIG = re.compile(r"^\s*(स|हे|ह|प)\s*[०o0]\s*[-—–~=]+\s*")         # स० Aruṇadatta, हे० Hemādri, प० Candranandana
OPEN = re.compile(r"अथा?तो.{0,40}व्याख्यास्यामः")                     # chapter opening (root text)
VNUM = re.compile(r"[॥|।!]{1,2}\s*([०-९]{1,3})\s*[॥|।!]{1,2}")

def clean(line):
    s = line.strip()
    if not s: return None
    letters = [ch for ch in s if not ch.isspace()]
    if len(letters) < 4 or sum(bool(DEV.match(ch)) for ch in letters) / len(letters) < 0.6: return None
    if re.search(r"टीकात्रयसंव|सटिप्पण|टीकाचय", s): return None       # running heads
    return s

lines = [clean(l) for l in open(src, encoding="utf-8")]
lines = [l for l in lines if l]
# join hyphenated breaks
text_lines, buf = [], ""
for l in lines:
    if buf: l = buf + l; buf = ""
    if l.endswith("-") and not SIG.match(l[-4:]): buf = l[:-1]; continue
    text_lines.append(l)

chapters, cur_ch, block, blocks = [], 0, None, []
def close():
    global block
    if block:
        t = " ".join(block["lines"])
        m = VNUM.search(t)
        if m: block["verse"] = int(m.group(1).translate(DIG)); t = t[:m.start()]
        block["deva"] = re.sub(r"\s+", " ", t).strip()
        if len(block["deva"]) > 20: blocks.append(block)
    block = None
for l in text_lines:
    if OPEN.search(l) and not SIG.match(l):
        close(); cur_ch += 1
    m = SIG.match(l)
    if m:
        close()
        if m.group(1) == "प": block = {"chapter": cur_ch, "lines": [l[m.end():]], "verse": None}
        continue
    if block is not None: block["lines"].append(l)
close()
for b in blocks:
    b["iast"] = transliterate(b["deva"], sanscript.DEVANAGARI, sanscript.IAST)
    del b["lines"]
json.dump(blocks, open(out, "w"), ensure_ascii=False, indent=0)
from collections import Counter
cc = Counter(b["chapter"] for b in blocks)
print("chapter openings found:", cur_ch, "| PC blocks:", len(blocks), "| with verse number:", sum(b["verse"] is not None for b in blocks))
print("blocks per chapter:", dict(sorted(cc.items())))
