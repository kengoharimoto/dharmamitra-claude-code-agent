#!/usr/bin/env python3
"""Assemble e-texts of the AHS commentaries from Surya OCR (see README.md).
Usage: assemble.py BOOK        BOOK = t1928 | parad
Output: etext/BOOK_*.txt, etext/BOOK_structure.jsonl, check/BOOK_report.json
"""
import glob, html, json, re, sys, unicodedata
from collections import Counter, defaultdict
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

BOOK = sys.argv[1]
P = "/mnt2/kengo/ocr-ahs-tika1928"
DE = "/mnt2/kengo/E-texts/1_sanskr/6_sastra/7_ayur/vagbhata_astangahrdaya.txt"
STH = {"sūtrasthāna": "Sū", "śārīrasthāna": "Śā", "nidānasthāna": "Ni", "cikitsāsthāna": "Ci", "kalpasthāna": "Ka", "uttarasthāna": "U"}
COMM = {"स": "arunadatta", "म": "arunadatta", "हे": "hemadri", "ह": "hemadri", "हृ": "hemadri", "ह्": "hemadri", "आर": "hemadri",
        "प": "candranandana", "ष": "candranandana",       # म, ह, ष: frequent OCR misreads of स, हे, प
        "आ२": "hemadri",                                 # आ० र० read as आ० २०
        "पचं": "candranandana", "पच": "candranandana"}   # प० च० = OCR of प० चं०                          # parad: प० चं० = Padārthacandrikā (edition's abbreviations)
NAMES = {"arunadatta": "Aruṇadatta, Sarvāṅgasundarā", "hemadri": "Hemādri, Āyurvedarasāyana",
         "candranandana": "Candranandana, Padārthacandrikā"}

# ---------------------------------------------------------------- Das & Emmerick verses (grouped)
def de_verses():
    units, chap, buf, invar = [], None, [], False
    def flush(ref=None):
        t = " ".join(buf).strip()
        if t and chap: units.append((chap, ref, re.sub(r"\s+", " ", t)))
        buf.clear()
    for line in open(DE, encoding="utf-8-sig"):
        s = line.strip()
        if invar:
            invar = "}" not in s; continue
        if "\\var{" in s:
            invar = "}" not in s[s.index("\\var{"):]; s = s[:s.index("\\var{")].strip()
        if not s or s.startswith("%"): continue
        m = re.match(r"^(\S+sthāna) (\d+)\s*$", s)
        if m and m.group(1) in STH:
            flush(); chap = f"{STH[m.group(1)]}.{m.group(2)}"; continue
        m = re.search(r"\|\|\s*([0-9]+(?:\.[0-9]+)?(?:™)?(?:\+\(?[0-9]+\)?)?[a-z]*)\s*\|\|\s*$", s)
        if m:
            buf.append(s[:m.start()].rstrip(" |")); flush(f"{chap}.{m.group(1).replace('™', '*')}")
        else:
            buf.append(s)
            if len(" ".join(buf)) > 600: flush()
    flush()
    # group pāda-numbered units (98a, 98b …) into one verse
    out = []
    for chap, ref, t in units:
        key = re.sub(r"[a-d]+$", "", ref) if ref else None
        if out and key and out[-1]["key"] == key and out[-1]["chap"] == chap:
            out[-1]["text"] += " | " + t
        else:
            out.append({"chap": chap, "key": key or f"{chap}.prose", "text": t})
    return out

# ---------------------------------------------------------------- normalisation
NASAL = {"ङ": "कखगघ", "ञ": "चछजझ", "ण": "टठडढ", "न": "तथदध", "म": "पफबभ"}
KEEP = re.compile(r"[अ-हा-्ंःॠ-ॣॐ]")
def norm_with_map(s):
    """skeleton for fuzzy matching + map from skeleton index to original index"""
    s = unicodedata.normalize("NFC", s)
    out, idx = [], []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in NASAL and i + 2 < len(s) and s[i + 1] == "्" and s[i + 2] in NASAL[ch]:
            out.append("ं"); idx.append(i); i += 2; continue            # class nasal → anusvāra
        if ch == "ँ": ch = "ं"                                      # candrabindu → anusvāra
        if KEEP.match(ch): out.append(ch); idx.append(i)
        i += 1
    return "".join(out), idx

def iast2deva(t):
    t = t.replace("’", "'").replace("|", " ")
    return transliterate(t, sanscript.IAST, sanscript.DEVANAGARI)

# ---------------------------------------------------------------- OCR pages
def pages():
    res = []
    for f in sorted(glob.glob(f"{P}/surya_out/{BOOK}/chunk_*/*/results.json")):
        start = int(re.search(r"chunk_(\d+)-", f).group(1))
        for k, pg in enumerate(next(iter(json.load(open(f)).values()))):
            res.append((start + k + 1, pg))                                     # 1-indexed pdf page
    return sorted(res, key=lambda x: x[0])

def block_text(b):
    t = b.get("html") or b.get("text") or ""
    t = re.sub(r"<br\s*/?>", "\n", t); t = re.sub(r"</p>\s*<p>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return t.strip()

FN_SEED = re.compile(r"(?:^|\s)[०-९]{1,2}\s*[‘'“\"]")
FN_MS = re.compile(r"पुस्तक|पाठ|(?:[कखगघङचजझटठड]\.?\s){2,}")
SKIP = {"PageHeader", "PageFooter", "Picture", "Figure", "Picture-group"}

stream, footnotes, headers, last_p = [], [], {}, None
for pno, pg in pages():
    H = pg.get("image_bbox", [0, 0, 0, 3600])[3]
    bl = sorted(pg["blocks"], key=lambda b: int(b.get("reading_order", 0)))
    headers[pno] = " ".join(block_text(b) for b in bl if b["label"] == "PageHeader")
    if BOOK == "parad":                                   # variant-reading footnotes
        seeds = [b["bbox"] for b in bl if b["label"] not in SKIP and b["bbox"][1] > 0.45 * H
                 and (b["label"] == "Footnote" or (FN_SEED.search(block_text(b)) and FN_MS.search(block_text(b))))]
    else:                                                 # t1928: the editor's notes, "( १ ) …"
        seeds = [b["bbox"] for b in bl if b["label"] not in SKIP and b["bbox"][1] > 0.3 * H
                 and (b["label"] == "Footnote" or re.match(r"\s*\(\s*[०-९]{1,2}\s*\)", block_text(b)))]
    # t1928: the notes can start lower in one column than in the other (p. 33: right column only), so a
    # block is a note only if it lies below a seed that overlaps it horizontally (same column, or a
    # full-width seed).
    def is_note(bb):
        if BOOK == "parad":                               # parad's notes run across both columns at the foot
            return bool(seeds) and bb[1] >= min(sd[1] for sd in seeds) - 15
        return any(bb[1] >= sd[1] - 15 and min(bb[2], sd[2]) - max(bb[0], sd[0]) > 0.3 * min(bb[2] - bb[0], sd[2] - sd[0])
                   for sd in seeds)
    for b in bl:
        if b["label"] in SKIP: continue
        t = block_text(b)
        if not t: continue
        if is_note(b["bbox"]):
            footnotes.append((pno, t)); continue
        if pno != last_p:
            stream.append(f"\uE000{pno}\uE001")              # exact page marker (ignored by matching)
            last_p = pno
        stream.append(t + "\n")
raw = "".join(stream)
# join line-final hyphenation (also across a page marker), then lines
raw = re.sub(r"[-‐]\n((?:\uE000\d+\uE001)?)(?=\S)", r"\1", raw)
text = re.sub(r"[ \t]*\n[ \t]*", " ", raw)
text = re.sub(r" {2,}", " ", text)
# Surya writes most line-end word breaks as "hyphen + space" inside a block (सर्व- हितावहाम्); gloss
# dashes in these editions carry no space (रसान्-मांसरसान्), so join only the spaced form
text = re.sub(r"([\u0900-\u097F])[-‐] (?=[\u0900-\u097F])", r"\1", text)
import bisect
_marks = [(m.start(), int(m.group(1))) for m in re.finditer(r"\uE000(\d+)\uE001", text)]
_mpos = [a for a, _ in _marks]
def page_of(i):
    k = bisect.bisect_right(_mpos, i) - 1
    return _marks[k][1] if k >= 0 else None
strip_marks = lambda t: re.sub(r"\s*\uE000\d+\uE001\s*", " ", t).strip()

N, nmap = norm_with_map(text)

# ---------------------------------------------------------------- locate mūla
verses = de_verses()
if BOOK == "t1928": verses = [v for v in verses if v["chap"].startswith("Sū.")]
# match half-verses: t1928 prints the mūla an ardha at a time with the commentaries after each half
units = []
for v in verses:
    halves = [h.strip() for h in v["text"].split(" | ") if h.strip()]
    if len(halves) == 1:
        units.append({"key": v["key"], "chap": v["chap"], "text": halves[0]})
    else:
        for h, lab in zip(halves, ["ab", "cd", "ef", "gh"]):
            units.append({"key": v["key"] + lab, "chap": v["chap"], "text": h})
unorm = []
for v in units:
    vn, _ = norm_with_map(iast2deva(v["text"]))
    unorm.append(vn)

def seek(k, p, windows=(1500, 5000, 15000, 40000)):
    """nearest acceptable occurrence of unit k at or after p"""
    vn = unorm[k]
    if len(vn) < 10: return None
    cut = 84 if len(vn) >= 30 else 90
    for W in windows:
        al = fuzz.partial_ratio_alignment(vn, N[p:p + W], score_cutoff=cut)
        if al: return (p + al.dest_start, p + al.dest_end, al.score)
    return None

def confirmed(k, hit, n=4, need=2):
    """do the next units follow shortly after this hit? (rejects quotations in prefaces and indexes)"""
    q, ok = hit[1], 0
    for j in range(k + 1, min(len(units), k + 1 + n)):
        h = seek(j, q, (1500, 5000, 15000))
        if h: ok += 1; q = h[1]
    return ok >= need

def anchor(k, p, span):
    """first confirmed occurrence of unit k in N[p:p+span]"""
    q = p
    while q < min(len(N), p + span):
        h = seek(k, q, (20000,))
        if not h: q += 18000; continue
        if confirmed(k, h): return h
        q = h[0] + 1
    return None

found, missing, p, streak = [], [], 0, 0
for k, v in enumerate(units):
    hit = anchor(k, 0, len(N)) if k == 0 else seek(k, p)
    if not hit and streak >= 6:                      # lost the thread: re-anchor further ahead
        hit = anchor(k, p, 600000)
    if not hit:
        missing.append(v["key"]); streak += 1; continue
    streak = 0
    a, b = nmap[hit[0]], nmap[min(hit[1], len(nmap)) - 1] + 1
    m = re.match(r"[^\u0905-\u0939]{0,3}?(?:।|॥)?\s*(?:[(\[]?[०-९0-9.\s-]{0,8}[)\]]?)?\s*(?:॥|।)?", text[b:b + 25])
    if m: b += m.end()
    found.append({"key": v["key"], "chap": v["chap"], "start": a, "end": b, "score": hit[2],
                  "agree": fuzz.ratio(unorm[k], N[hit[0]:hit[1]])})
    p = hit[1]

# ---------------------------------------------------------------- segment commentary
SIG = re.compile(r"(?:(?<=[\s।॥”\"'\uE001])|^)(प\s*[०o0.]\s*चं?|स|म|हे|हृ|ह्|ह|प|ष|आ\s*[०o0.]?\s*[र२])\s*[०o0.]\s*[-—–~=]+\s*")
# Weak variants, accepted only right after a closing verse number, at the top of a page or at region start:
# स्०/सू० for स०; and a siglum missing either its ० (हे--) or its dash (स० इत्यनया …).
SIG_WEAK = re.compile(r"(?:^\s*|\uE001\s*|॥\s*[०-९0-9]+\s*॥\s*)(स्|सू|हे|हृ|ह्|स|प)(?:\s*[०o0.]\s*[-—–~=]*|\s*[-—–~=]+)\s*")
VEND = re.compile(r"॥\s*[०-९0-9]+(?:\s*[-–,]\s*[०-९0-9]+)*\s*॥")
segs = []
segs.append({"type": "frontmatter", "ref": None, "start": 0, "end": found[0]["start"] if found else len(text)})
for k, f in enumerate(found):
    segs.append({"type": "mula", "ref": f["key"], "start": f["start"], "end": f["end"]})
    r0, r1 = f["end"], found[k + 1]["start"] if k + 1 < len(found) else len(text)
    region = text[r0:r1]
    cuts = [(m.start(), m.end(), COMM[re.sub(r"[\s०o0.]", "", m.group(1))]) for m in SIG.finditer(region)]
    # weak siglum variants (स्०, सू० for स०) only right after a closing verse number or at region start
    for m in SIG_WEAK.finditer(region):
        if not any(a <= m.start() < b for a, b, _ in cuts):
            cuts.append((m.start(1), m.end(), "arunadatta" if m.group(1) in ("स्", "सू") else COMM[m.group(1)]))
    # "प्र. टी." (t1928, Sū.13.15 only): a further gloss printed beside the three commentaries; kept apart
    for m in re.finditer(r"(?<=[\s।॥])प्र\s*[.०]\s*टी\s*[.०]\s*[-—–]+\s*", region):
        cuts.append((m.start(), m.end(), "pratika-tika"))
    cuts.sort()
    if not cuts:
        if region.strip(): segs.append({"type": "lead", "ref": f["key"], "start": r0, "end": r1})
        continue
    if region[:cuts[0][0]].strip():
        segs.append({"type": "lead", "ref": f["key"], "start": r0, "end": r0 + cuts[0][0]})
    for c, (s0, s1, who) in enumerate(cuts):
        e = cuts[c + 1][0] if c + 1 < len(cuts) else len(region)
        seg = {"type": "comm", "who": who, "ref": f["key"], "start": r0 + s1, "end": r0 + e}
        if c + 1 == len(cuts):                                          # trailing lead-in to next verse
            ends = list(VEND.finditer(region, s1, e))
            if ends and region[ends[-1].end():e].strip():
                seg["end"] = r0 + ends[-1].end()
                segs.append(seg)
                segs.append({"type": "lead", "ref": found[k + 1]["key"] if k + 1 < len(found) else f["key"],
                             "start": r0 + ends[-1].end(), "end": r0 + e})
                continue
        segs.append(seg)
for s in segs:
    if s.get("who") == "pratika-tika": s["type"], s["siglum"] = "unassigned", "प्र. टी."; del s["who"]
    s["text"] = strip_marks(text[s["start"]:s["end"]])
    if s["type"] == "lead" and len(s["text"]) > 300:
        s["type"] = "unassigned"          # editor's ṭippaṇī or commentary whose siglum OCR lost
    s["page"] = page_of(s["start"])
segs = [s for s in segs if s["text"]]
# repair: the matcher can take a commentary's own quotation of the verse for the printed mūla. Then the
# commentary is cut and its continuation lands in "unassigned". If the commentary before that "mūla" is
# still open (no closing verse number), give the quotation and the continuation back to it.
for k in range(2, len(segs)):
    s, m, c = segs[k], segs[k - 1], segs[k - 2]
    if s["type"] == "unassigned" and m["type"] == "mula" and c["type"] == "comm" and not VEND.search(c["text"][-40:]):
        m["type"], m["who"], m["quote"] = "comm", c["who"], True
        s["type"], s["who"] = "comm", c["who"]
# Manual corrections from the page-image check of misfiling suspects (siglcheck/, 2026-10-31): where the
# siglum is unreadable in the OCR, the passage starting at `anchor` (on `page` ±1) is given to `who` up to the
# end of its paragraph (the next closing verse number) or of the segment.
for o in json.load(open(f"{P}/check/sigla_overrides.json")):
    if o["book"] != BOOK: continue
    for k, s in enumerate(segs):
        a = s["text"].find(o["anchor"]) if s["type"] == "comm" and abs(s["page"] - o["page"]) <= 1 else -1
        if a < 0: continue
        m = VEND.search(s["text"], a); e = m.end() if m else len(s["text"])
        parts = [dict(s, text=s["text"][:a].strip()), dict(s, text=s["text"][a:e].strip(), who=o["who"], override=True),
                 dict(s, text=s["text"][e:].strip())]
        segs[k:k + 1] = [x for x in parts if x["text"]]
        break
    else:
        print("override not applied:", o["anchor"])
# parad prints Aruṇadatta without a siglum where he is the only commentator (e.g. most of Śārīrasthāna,
# where Hemādri is lost); its editor's notes are footnotes, already set aside. So unmarked commentary
# in the main text is Aruṇadatta's there.
if BOOK == "parad":
    for s in segs:
        if s["type"] == "unassigned": s["type"], s["who"], s["nosig"] = "comm", "arunadatta", True

# ---------------------------------------------------------------- write
import os
os.makedirs(f"{P}/etext", exist_ok=True); os.makedirs(f"{P}/check", exist_ok=True)
with open(f"{P}/etext/{BOOK}_structure.jsonl", "w") as fo:
    for s in segs: fo.write(json.dumps({k: s[k] for k in ("type", "who", "ref", "page", "quote", "nosig", "override", "siglum", "text") if k in s}, ensure_ascii=False) + "\n")

def write(name, items, head):
    with open(f"{P}/etext/{BOOK}_{name}.txt", "w") as fd, open(f"{P}/etext/{BOOK}_{name}.iast.txt", "w") as fi:
        for f_, conv in ((fd, lambda t: t), (fi, lambda t: transliterate(t, sanscript.DEVANAGARI, sanscript.IAST))):
            f_.write(f"% {head}\n% OCR: Surya OCR 2, assembled by assemble.py; refs = Das & Emmerick verse numbers; [p. N] = pdf page\n\n")
            chap = None
            for s in items:
                c = s["ref"].rsplit(".", 1)[0] if s.get("ref") else None
                if c != chap and c:
                    f_.write(f"\n## {c}\n\n"); chap = c
                f_.write(f"[{s['ref']}] [p. {s['page']}] {conv(s['text'])}\n")

for who in sorted({s["who"] for s in segs if s["type"] == "comm"}):
    write(who, [s for s in segs if s["type"] == "comm" and s["who"] == who], NAMES[who])
write("mula", [s for s in segs if s["type"] == "mula"], "Aṣṭāṅgahṛdaya, mūla as printed")
write("leadins", [s for s in segs if s["type"] == "lead"], "Lead-ins (avataraṇikās) printed before the mūla")
write("unassigned", [s for s in segs if s["type"] == "unassigned"], "Unassigned passages (editor's notes, or commentary whose siglum was not recognised)")
with open(f"{P}/etext/{BOOK}_frontmatter.txt", "w") as fo:
    fo.write("\n\n".join(s["text"] for s in segs if s["type"] == "frontmatter"))
with open(f"{P}/etext/{BOOK}_footnotes.txt", "w") as fo:
    for pno, t in footnotes: fo.write(f"[p. {pno}] {t}\n")

# ---------------------------------------------------------------- report
by_sth = defaultdict(lambda: [0, 0])
for v in verses: by_sth[v["chap"].split(".")[0]][1] += 1
vfound = {re.sub(r"(ab|cd|ef|gh)$", "", f["key"]) for f in found}
for v in verses:
    if v["key"] in vfound: by_sth[v["chap"].split(".")[0]][0] += 1
L = sum(len(norm_with_map(text[f["start"]:f["end"]])[0]) for f in found)
agree = sum(f["agree"] * len(norm_with_map(text[f["start"]:f["end"]])[0]) for f in found) / max(1, L)
regular = [v for v in verses if "+" not in v["key"] and "*" not in v["key"]]
reg_found = vfound
rep = {"book": BOOK, "pages": len(headers), "verses_total": len(verses), "verses_found": len(vfound),
       "half_units_found": f"{len(found)}/{len(units)}",
       "regular_verses_found": f"{sum(v['key'] in reg_found for v in regular)}/{len(regular)}",
       "by_sthana": {k: f"{a}/{b}" for k, (a, b) in by_sth.items()},
       "mula_letter_agreement_with_DE_pct": round(agree, 2),
       "segments": dict(Counter(s["type"] + (":" + s["who"] if s.get("who") else "") for s in segs)),
       "chars": {k: sum(len(s["text"]) for s in segs if (s["type"] + (":" + s.get("who", "") if s.get("who") else "")) == k)
                 for k in {s["type"] + (":" + s["who"] if s.get("who") else "") for s in segs}},
       "footnote_blocks": len(footnotes), "missing_verses": missing}
# printed page numbers from the running heads: leaves missing from the scan. Track the offset
# pdf - printed; a lost leaf lowers it for good (an inserted plate raises it). Changes must persist.
D = str.maketrans("०१२३४५६७८९", "0123456789")
offs = {pno: {pno - int(x.translate(D)) for x in re.findall(r"[०-९0-9]{1,4}", headers[pno])} for pno in sorted(headers)}
pl = sorted(offs)
gaps, cur = [], None
for k, pno in enumerate(pl):
    if cur is None:
        win = Counter(o for q in pl[k:k + 8] for o in offs[q])
        if win and win.most_common(1)[0][1] >= 5: cur = win.most_common(1)[0][0]
        continue
    if cur in offs[pno]: continue
    for d in (2, 1, 3, 4, 5, 6, -1, -2, -3, -4):
        if all(cur - d in offs[q] or not offs[q] for q in pl[k:k + 4]) and sum(cur - d in offs[q] for q in pl[k:k + 4]) >= 3:
            if d > 0: gaps.append({"before_pdf_page": pno, "printed_missing": list(range(pno - cur, pno - cur + d))})
            else: gaps.append({"before_pdf_page": pno, "unnumbered_inserted": -d})
            cur -= d; break
    else:
        win = Counter(o for q in pl[k:k + 8] for o in offs[q])
        if win and win.most_common(1)[0][1] >= 5 and win.most_common(1)[0][0] != cur:
            cur = win.most_common(1)[0][0]                   # new numbering sequence (e.g. front matter → text)
rep["printed_pages_missing_from_scan"] = gaps
json.dump(rep, open(f"{P}/check/{BOOK}_report.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "missing_verses"}, ensure_ascii=False, indent=1))
print("missing (first 30):", missing[:30])
