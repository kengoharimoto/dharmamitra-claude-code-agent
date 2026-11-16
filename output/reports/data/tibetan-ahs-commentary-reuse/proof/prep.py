#!/usr/bin/env python3
"""Proofreading packages: per page, crops of every text block (300 dpi) + the block's OCR text.
Usage: prep.py BOOK FIRST LAST OUTDIR   -> OUTDIR/pNNN_bKK[_partN].png, OUTDIR/pages.json"""
import glob, html, json, re, subprocess, sys
from PIL import Image
P = "/mnt2/kengo/ocr-ahs-tika1928"
book, a, b, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
pdf = {"t1928": f"{P}/src/ahs_tika1928.pdf", "parad": "/qnap/kengo/dox/Books_and_Articles_on_iCloud/Ashtanga.Hridaya.of.Vagbhata.pdf"}[book]
def block_text(b):
    t = b.get("html") or b.get("text") or ""
    t = re.sub(r"<br\s*/?>", "\n", t); t = re.sub(r"</p>\s*<p>", "\n", t)
    return html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
PG = {}
for f in sorted(glob.glob(f"{P}/surya_out/{book}/chunk_*/*/results.json")):
    s = int(re.search(r"chunk_(\d+)-", f).group(1))
    for k, pg in enumerate(next(iter(json.load(open(f)).values()))): PG[s + k + 1] = pg
res = []
for p in range(a, b + 1):
    pg = PG[p]; fn = f"{out}/full_p{p:03d}"
    subprocess.run(["pdftoppm", "-f", str(p), "-l", str(p), "-r", "300", "-gray", "-png", "-singlefile", pdf, fn], check=True)
    im = Image.open(fn + ".png"); s = im.size[0] / pg["image_bbox"][2]
    blocks = []
    for bl in sorted(pg["blocks"], key=lambda x: int(x.get("reading_order", 0))):
        if bl["label"] in ("PageHeader", "PageFooter", "Picture", "Figure"): continue
        t = block_text(bl)
        if not t: continue
        x0, y0, x1, y1 = bl["bbox"]; parts = []
        n = max(1, round((y1 - y0) / 450))
        for i in range(n):
            ya = y0 + (y1 - y0) * i / n - (8 if i else 6); yb = y0 + (y1 - y0) * (i + 1) / n + 8
            c = f"{out}/p{p:03d}_b{bl['reading_order']:02d}" + (f"_part{i+1}" if n > 1 else "") + ".png"
            im.crop((int((x0 - 12) * s), int(ya * s), int((x1 + 12) * s), int(yb * s))).save(c); parts.append(c)
        blocks.append({"block": bl["reading_order"], "label": bl["label"], "crops": parts, "ocr": t})
    res.append({"page": p, "full": fn + ".png", "blocks": blocks})
json.dump(res, open(f"{out}/pages.json", "w"), ensure_ascii=False, indent=1)
print(len(res), "pages", sum(len(r["blocks"]) for r in res), "blocks")
