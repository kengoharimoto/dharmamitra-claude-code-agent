#!/usr/bin/env python3
"""Crop the page image around each misfiling cluster (clusters.json) so the governing siglum can be read.
Each crop: the column from ~18 lines above the estimated cluster start to ~5 lines below; a red line marks
the estimated start (estimated from the character offset inside Surya's text block).
Usage: python3 -P crops.py CLUSTERS_JSON OUTDIR          (needs pdftoppm, PIL)"""
import glob, html, json, re, subprocess, sys, os
from PIL import Image, ImageDraw
from rapidfuzz import fuzz
P = "/mnt2/kengo/ocr-ahs-tika1928"
cl = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
S = [json.loads(l) for l in open(f"{P}/etext/t1928_structure.jsonl")]
pages = {}
for f in sorted(glob.glob(f"{P}/surya_out/t1928/chunk_*/*/results.json")):
    st = int(re.search(r"chunk_(\d+)-", f).group(1))
    for k, pg in enumerate(next(iter(json.load(open(f)).values()))): pages[st + k + 1] = pg
def btext(b): return html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>", " ", b.get("html") or "")))
imgcache = {}
def page_img(p):
    if p not in imgcache:
        fn = f"{out}/_p{p}"
        if not os.path.exists(fn + ".png"):
            subprocess.run(["pdftoppm", "-f", str(p), "-l", str(p), "-r", "200", "-gray", "-png", "-singlefile", f"{P}/src/ahs_tika1928.pdf", fn], check=True)
        imgcache.clear(); imgcache[p] = Image.open(fn + ".png").convert("RGB")
    return imgcache[p]
for n, c in enumerate(cl):
    seg = S[c["seg"]]["text"]
    # Devanagari position of the cluster start ~ proportional to the IAST offset
    pos = int(c["start"] / max(c["seglen"], 1) * len(seg))
    snip = seg[pos:pos + 40] if len(seg) - pos > 20 else seg[-40:]
    best = None
    for p in range(c["page"], c["page"] + 4):
        if p not in pages: continue
        for bi, b in enumerate(pages[p]["blocks"]):
            if b["label"] in ("PageHeader", "PageFooter", "Picture"): continue
            t = btext(b)
            if len(t) < 10: continue
            al = fuzz.partial_ratio_alignment(snip, t)
            if best is None or al.score > best[0]: best = (al.score, p, bi, al.dest_start / max(len(t), 1))
    if not best: c["crop"] = None; continue
    score, p, bi, frac = best
    pg = pages[p]; b = pg["blocks"][bi]; W = pg["image_bbox"][2]
    img = page_img(p); s = img.width / W
    x0, y0, x1, y1 = b["bbox"]; ys = y0 + frac * (y1 - y0)
    lh = 49
    top, bot = max(0, ys - 18 * lh), min(pg["image_bbox"][3], ys + 5 * lh)
    crop = img.crop((int((x0 - 15) * s), int(top * s), int((x1 + 15) * s), int(bot * s)))
    d = ImageDraw.Draw(crop); yy = int((ys - top) * s)
    d.line([(0, yy), (crop.width, yy)], fill=(255, 0, 0), width=2)
    fn = f"{out}/c{n:03d}_p{p}.png"; crop.save(fn)
    c.update(crop=fn, crop_page=p, crop_block=bi, locate_score=round(score), block_top_in_crop=y0 >= top)
json.dump(cl, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print("crops", sum(1 for c in cl if c.get("crop")), "| weak location (<80):", sum(1 for c in cl if c.get("crop") and c["locate_score"] < 80))
