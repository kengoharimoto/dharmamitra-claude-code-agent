# Proofreading brief: AHS commentaries, 1928 edition (Sū.1, 6, 7)

You are proofreading Surya OCR output of a 1928 Devanagari edition of the Aṣṭāṅgahṛdaya (Sūtrasthāna) with three
Sanskrit commentaries printed after each root verse: स० = Aruṇadatta, प० = Candranandana, हे० = Hemādri.
The root text (mūla) is in large type; commentaries in small type; editor's notes ("( १ ) …") at the foot.

**Goal: the e-text must reproduce the printed page exactly.** Correct OCR errors only. Do not normalise
spelling (keep the print's anusvāra vs. class nasal, sandhi, avagraha, punctuation), do not modernise, do not
emend the author. If the print itself has an obvious misprint, record it as kind `print` (it is not applied).

## Your input
A task file (JSON list of pages). For each page: `full` = whole-page PNG; `blocks` = text blocks in reading order,
each with `block` (number), `crops` (one or more PNGs of that block, top to bottom) and `ocr` (the OCR text).

## Procedure, for every block of every page
1. Read each crop image of the block (Read tool) and compare it, line by line, with `ocr`.
2. For every difference record a correction with
   `python3 -P /mnt2/kengo/ocr-ahs-tika1928/proof/add.py BATCH PAGE BLOCK KIND CONF 'OLD' 'NEW' 'NOTE'`
   - OLD: an exact substring of that block's `ocr`, long enough to occur once (≈ 2–4 words around the error).
     The script refuses OLD strings that are not unique; then lengthen OLD.
   - NEW: the same stretch as printed.
   - KIND: `ocr` (letters printed clearly, misread), `restored` (letters physically lost: the scan clips the outer
     edge of many columns, so the first or last akṣara of a line is often cut or missing; also blots/gaps),
     `missing` (OCR skipped words or a whole line: OLD = text just before the gap, NEW = OLD + missing text),
     `print` (printer's error; not applied).
   - CONF: `high` (clearly legible / certain), `medium`, `low`.
   - NOTE: short, e.g. "edge clipped; Parāḍkar has समासतो".
3. For `restored` letters use sense, grammar and parallels. The helper
   `python3 -P /mnt2/kengo/ocr-ahs-tika1928/proof/parallel.py "SNIPPET"` finds the best match of a snippet in
   Parāḍkar's Aruṇadatta/Hemādri, the 1928 streams of all three commentators, the AHS root text, the Saṃgraha,
   Caraka and Suśruta. Aruṇadatta often copies Candranandana, and Parāḍkar is a second edition of Aruṇadatta and
   Hemādri, so the helper usually supplies the lost letters. Prefer what the print shows; restore only what is lost.
   (Parāḍkar's OCR drops many anusvāra/visarga dots — don't copy those losses.)

## What to ignore
- Line-break hyphens ("नासा- ननुगतार्था"): they are joined automatically. Only correct the letters around them if wrong.
- Spaces and line breaks; the spacing between a word and a daṇḍa.
- Running heads and page numbers (not included).
- The number of dashes after a siglum (स०- vs स०--).
- ब vs व: correct only where the print clearly shows the other letter; otherwise leave as the OCR has it
  (this will be handled separately).

## Known OCR habits (from a pilot on pp. 35–36; look out for them)
घ्न read as न्न/ध्न; ृ dropped from हृ (हृन्नाभि → हन्नाभि); ह्न read as ह (अह्नो → अहो); anusvāra dropped (भवंति → भवति);
ग्नि read as भि; ड्र, ष/प, भ/म confusions; on clipped edges the first akṣara of a line missing or misread.

## What matters most
- Sigla (स०, प०, हे० and the dash after them): an OCR misreading of a siglum (म०, ष०, ह०, हृ०, स्व०…) **must** be corrected,
  because sigla decide which commentator the text is filed under.
- Verse numbers ॥ ७ ॥ and daṇḍas.
- Lines skipped by the OCR (compare the number of printed lines with the OCR).
- Edge-clipped akṣaras.

## Be careful
- Do not "correct" a reading because a parallel differs: the editions and commentators differ genuinely.
  Change only where the print shows something else, or where the print is physically lost.
- Do not invent: if you cannot read it and cannot restore it with reasonable confidence, use CONF `low` and say so.
- Work through all blocks; don't skip blocks that look clean — but clean blocks need no entries.

## Final report (your last message, short)
Pages done; number of corrections by kind; any block whose crop did not match its OCR (wrong crop, text missing
from both); pages with special problems (damaged, unreadable); and 3–5 sample corrections you are least sure of.
