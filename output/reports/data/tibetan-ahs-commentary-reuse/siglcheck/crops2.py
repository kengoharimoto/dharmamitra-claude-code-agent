#!/usr/bin/env python3
"""Second-pass crops for unclear / edge-cut items: wider margins (+60 px each side) and from the TOP of the
text block containing the passage (where its siglum is printed); if that block begins at the top of a column
(continuation from the previous column/page), the previous block in reading order is prepended.
Usage: python3 -P crops2.py CLUSTERS_JSON IDS(comma) OUTDIR"""
import glob, html, json, re, subprocess, sys, os
from PIL import Image, ImageDraw
P = "/mnt2/kengo/ocr-ahs-tika1928"
cl = json.load(open(sys.argv[1])); ids = [int(x) for x in sys.argv[2].split(",")]; out = sys.argv[3]; os.makedirs(out, exist_ok=True)
pages = {}
for f in sorted(glob.glob(f"{P}/surya_out/t1928/chunk_*/*/results.json")):
    st = int(re.search(r"chunk_(\d+)-", f).group(1))
    for k, pg in enumerate(next(iter(json.load(open(f)).values()))): pages[st + k + 1] = pg
def img(p):
    fn = f"{P}/siglcheck/crops/_p{p}"
    if not os.path.exists(fn + ".png"):
        subprocess.run(["pdftoppm", "-f", str(p), "-l", str(p), "-r", "200", "-gray", "-png", "-singlefile", f"{P}/src/ahs_tika1928.pdf", fn], check=True)
    return Image.open(fn + ".png").convert("RGB")
def text_blocks(p):
    return [b for b in sorted(pages[p]["blocks"], key=lambda b: int(b.get("reading_order", 0))) if b["label"] not in ("PageHeader", "PageFooter", "Picture")]
for i in ids:
    c = cl[i]; p = c["crop_page"]; pg = pages[p]; b = pg["blocks"][c["crop_block"]]
    W, H = pg["image_bbox"][2], pg["image_bbox"][3]
    im = img(p); s = im.width / W
    parts = []
    # previous block (reading order) if this block starts at a column top
    tb = text_blocks(p); k = next((j for j, x in enumerate(tb) if x is b), None)
    if b["bbox"][1] < 0.2 * H:
        if k and k > 0: pb, pp = tb[k - 1], p
        elif p - 1 in pages and text_blocks(p - 1): pb, pp = text_blocks(p - 1)[-1], p - 1
        else: pb = None
        if pb is not None:
            pim = img(pp); ps = pim.width / pages[pp]["image_bbox"][2]
            x0, y0, x1, y1 = pb["bbox"]; y0 = max(y0, y1 - 1200)
            parts.append(pim.crop((int((x0 - 60) * ps), int(y0 * ps), int((x1 + 60) * ps), int(y1 * ps))))
    x0, y0, x1, y1 = b["bbox"]
    est = c.get("est_y") or (y0 + 0.5 * (y1 - y0))
    cr = im.crop((int(max(0, x0 - 60) * s), int(y0 * s), int(min(W, x1 + 60) * s), int(y1 * s)))
    parts.append(cr)
    wid = max(x.width for x in parts); hh = sum(x.height for x in parts) + 12 * (len(parts) - 1)
    canvas = Image.new("RGB", (wid, hh), (255, 255, 255)); y = 0
    for j, x in enumerate(parts):
        canvas.paste(x, (0, y)); y += x.height
        if j < len(parts) - 1:
            ImageDraw.Draw(canvas).rectangle([0, y, wid, y + 11], fill=(0, 0, 255)); y += 12
    if canvas.height > 2600: canvas = canvas.resize((int(canvas.width * 2600 / canvas.height), 2600))
    fn = f"{out}/c{i:03d}_full.png"; canvas.save(fn); c["crop2"] = fn
json.dump(cl, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print("done", len(ids))
