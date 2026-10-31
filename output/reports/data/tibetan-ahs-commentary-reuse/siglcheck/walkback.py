#!/usr/bin/env python3
"""For a cluster, stack crops of its text block and of the blocks before it in reading order (across columns
and pages) back to the first block that opens with a siglum-like "X०—" (or at most MAXB blocks).
Long blocks are shown as top 8 lines + bottom 4 lines.  Usage: python3 -P walkback.py CLUSTERS IDS OUTDIR"""
import glob, html, json, re, subprocess, sys, os
from PIL import Image, ImageDraw
P = "/mnt2/kengo/ocr-ahs-tika1928"; MAXB = 5
cl = json.load(open(sys.argv[1])); ids = [int(x) for x in sys.argv[2].split(",")]; out = sys.argv[3]; os.makedirs(out, exist_ok=True)
pages = {}
for f in sorted(glob.glob(f"{P}/surya_out/t1928/chunk_*/*/results.json")):
    st = int(re.search(r"chunk_(\d+)-", f).group(1))
    for k, pg in enumerate(next(iter(json.load(open(f)).values()))): pages[st + k + 1] = pg
bt = lambda b: html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>", " ", b.get("html") or "")))
def img(p):
    fn = f"{P}/siglcheck/crops/_p{p}"
    if not os.path.exists(fn + ".png"):
        subprocess.run(["pdftoppm", "-f", str(p), "-l", str(p), "-r", "200", "-gray", "-png", "-singlefile", f"{P}/src/ahs_tika1928.pdf", fn], check=True)
    return Image.open(fn + ".png").convert("RGB")
def tblocks(p):
    return [b for b in sorted(pages[p]["blocks"], key=lambda b: int(b.get("reading_order", 0))) if b["label"] not in ("PageHeader", "PageFooter", "Picture")]
SIGLIKE = re.compile(r"^\s*\S{0,3}\s*[०o0.]\s*[-—–]")
def crop(p, b, s):
    x0, y0, x1, y1 = b["bbox"]; im = img(p); W = pages[p]["image_bbox"][2]; k = im.width / W
    c = im.crop((int(max(0, x0 - 40) * k), int(y0 * k), int(min(W, x1 + 40) * k), int(y1 * k)))
    lh = int(49 * k)
    if c.height > 13 * lh:   # top 8 lines … bottom 4 lines
        top, bot = c.crop((0, 0, c.width, 8 * lh)), c.crop((0, c.height - 4 * lh, c.width, c.height))
        c = Image.new("RGB", (c.width, top.height + bot.height + 8), (255, 255, 255)); c.paste(top, (0, 0)); c.paste(bot, (0, top.height + 8))
        ImageDraw.Draw(c).line([(0, top.height + 4), (c.width, top.height + 4)], fill=(0, 160, 0), width=3)
    ImageDraw.Draw(c).text((4, 2), f"p{p}", fill=(255, 0, 0))
    return c
for i in ids:
    c = cl[i]; p = c["crop_page"]; tb = tblocks(p); b = pages[p]["blocks"][c["crop_block"]]
    k = next(j for j, x in enumerate(tb) if x is b)
    seq = [(p, b)]
    while len(seq) < MAXB and not SIGLIKE.match(bt(seq[0][1])):
        if k > 0: k -= 1
        else:
            p -= 1; tb = tblocks(p); k = len(tb) - 1
        seq.insert(0, (p, tb[k]))
    parts = [crop(pp, bb, 1) for pp, bb in seq]
    W = max(x.width for x in parts); H = sum(x.height + 14 for x in parts)
    can = Image.new("RGB", (W, H), (255, 255, 255)); y = 0
    for x in parts:
        can.paste(x, (0, y)); y += x.height
        ImageDraw.Draw(can).rectangle([0, y + 2, W, y + 11], fill=(0, 0, 255)); y += 14
    if can.height > 3000: can = can.resize((int(can.width * 3000 / can.height), 3000))
    can.save(f"{out}/w{i:03d}.png"); print(i, [(pp, bt(bb)[:25]) for pp, bb in seq])
