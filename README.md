# scope-finder

Finds overhead door, loading dock and smoke curtain scope in a commercial bid set, with page references, and flags spec sections the table of contents lists but the set doesn't actually include.

## Why

Estimators at overhead door and dock contractors do takeoffs by hand from PDF drawing sets and spec books that can run to hundreds of pages. The scope is scattered:

- Door schedules sit on the A-600 sheets.
- Overhead coiling doors are specified in section 08 33 23, sectional doors in 08 36 13.
- Dock equipment is often buried in Division 11, "if at all," as one estimator put it.
- Smoke curtains can show up only in the specs, sometimes inside another trade's section (the elevator section, for example).
- Sometimes the table of contents lists a section that isn't in the set, and someone has to go hunting for it.

Finding and pulling those pages is slow, low-value work, and a missed item means an underpriced bid.

## How this version came about

My first attempt (2025) sent whole PDFs to an LLM through an n8n workflow and emailed back a summary. It worked on small files and broke on real ones: one drawing set was about 900 pages and 161 MB, far more than one request can take, and the results drifted. Companies also have IT reviews that make sending bid documents to a public AI tool a hard sell.

So this version does the part that should be predictable: plain text search, page by page, with page numbers. No AI reads the documents, and every result can be checked by opening the page it points to.

## What it does

- Reports, for each spec section in `rules.json`, whether it's **Found** (and on which pages), **Listed but missing** (in the table of contents, not in the book), or **Not in this set**.
- Finds keyword mentions anywhere in the specs and drawings (smoke curtains, dock levelers, coiling and sectional doors), so scope filed under an unexpected section still turns up.
- Guesses the drawing sheet number (A-601, etc.) from the title block text.
- Flags pages with no text layer (scanned sheets) so you know what wasn't searched.
- Writes `summary.md`, `summary.csv`, and `scope_packet.pdf`: every matching page in one file, once, with a cover summary and a bookmark per item.

## What it doesn't do (yet)

- **No counts.** It finds the pages; it doesn't read the door schedule table or count doors. That's the next step, and the one to get right by comparing against hand takeoffs.
- **No OCR.** Scanned sheets are flagged, not read.
- **Keyword matches can be noise.** In the sample, the painting section mentions "dock seal fabric" and gets flagged. A person still reviews the list; the tool just makes sure they look in the right places.
- Sheet numbers are a best guess from the page text.

## Run it

```
pip install -r requirements.txt
python sample/make_sample.py          # builds a small, made-up bid set
python scope_finder.py --specs sample/specs.pdf --drawings sample/drawings.pdf --out sample_output
```

Sample results are in [`sample_output/summary.md`](sample_output/summary.md). The sample set is fictional; no real project documents are in this repo.

To watch for other sections or words, edit `rules.json`.

## Next

1. Run it next to hand takeoffs on real bid sets and record what it misses.
2. Read door schedule tables into rows (mark, type, size, quantity) where the PDF has a text layer.
3. OCR for scanned sheets, page by page.

Built with Python, pypdf and reportlab, with help from Claude as a coding assistant. The rules and test cases come from an estimator's description of how takeoffs actually work.
