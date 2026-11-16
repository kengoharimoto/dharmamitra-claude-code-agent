#!/usr/bin/env python3
"""Record one proofreading correction.
Usage: python3 -P add.py BATCH PAGE BLOCK KIND CONF 'OLD' 'NEW' ['NOTE']
  KIND: ocr (misread print) | restored (letters lost on the scan, restored from sense/parallels) |
        missing (OCR skipped text: OLD = the text just before the gap, NEW = OLD + the missing text) |
        print (printer's error: recorded only, NOT applied; NEW = suggested reading)
  CONF: high | medium | low
OLD must occur exactly once in that block's OCR text (copy it from pages.json / the task file)."""
import json, sys, os, glob
P = os.path.dirname(os.path.abspath(__file__))
batch, page, block, kind, conf, old, new = sys.argv[1:8]; note = sys.argv[8] if len(sys.argv) > 8 else ""
page, block = int(page), int(block)
assert kind in ("ocr", "restored", "missing", "print"), "bad KIND"
assert conf in ("high", "medium", "low"), "bad CONF"
ocr = None
for f in glob.glob(f"{P}/t1928/*/pages.json"):
    for r in json.load(open(f)):
        if r["page"] == page:
            for b in r["blocks"]:
                if b["block"] == block: ocr = b["ocr"]
if ocr is None: sys.exit(f"ERROR: no block {block} on page {page}")
n = ocr.count(old)
if n != 1: sys.exit(f"ERROR: OLD occurs {n} times in p{page} b{block}; give a longer/exact OLD")
out = f"{P}/t1928/corr_{batch}.jsonl"
with open(out, "a") as fo:
    fo.write(json.dumps(dict(page=page, block=block, kind=kind, conf=conf, old=old, new=new, note=note), ensure_ascii=False) + "\n")
print("ok", sum(1 for _ in open(out)))
