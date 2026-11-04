"""scope_finder: find door and dock scope in a bid set, with page references.

Reads a spec book and a drawing set (PDFs with a text layer) and reports, for each
spec section and keyword you care about, which pages it is on. It also flags spec
sections the table of contents lists but the book doesn't contain, and pages with no
text layer (scanned sheets that would need OCR). No AI reads the documents: every
result is a plain text match you can check by opening the page.

Usage:
    python scope_finder.py --specs specs.pdf --drawings drawings.pdf --out output
"""
import argparse
import csv
import json
import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter

HERE = Path(__file__).parent


def section_pattern(number):
    # Any mention of the number. "08 33 23" also matches "083323", "08  33  23" and "08 33 23.13"-style subsections
    a, b, c = number.split()
    return re.compile(rf"\b{a}\s*{b}\s*{c}\b")


def own_page_pattern(number):
    """Marks a page that belongs to the section itself, not one that only mentions it.

    Matches the section's heading at the start of a line ("SECTION 08 33 23 - OVERHEAD COILING DOORS",
    "END OF SECTION 08 33 23") or its page footer ("08 33 23 - 4"). A cross-reference such as
    "Coordinate with Section 08 33 23." matches neither, so it can't make a missing section look present.
    """
    a, b, c = number.split()
    num = rf"{a}\s*{b}\s*{c}(?:\.\d+)?"
    heading = rf"^[ \t]*(?:END\s+OF\s+)?SECTION\s+{num}[ \t]*(?:[-–—:]|$)"
    footer = rf"\b{num}[ \t]*[-–—][ \t]*\d{{1,3}}\b"
    return re.compile(rf"{heading}|{footer}", re.IGNORECASE | re.MULTILINE)


def read_pages(path):
    reader = PdfReader(str(path))
    try:
        # PyMuPDF reads text much faster on big drawing sets (about 13 s vs 5 min on a 1,168-page bid set)
        import pymupdf
        with pymupdf.open(str(path)) as doc:
            return reader, [page.get_text() for page in doc]
    except ImportError:
        pass
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            texts.append("")
    return reader, texts


def find_toc_pages(texts, max_pages=15):
    return [i for i, t in enumerate(texts[:max_pages]) if "table of contents" in t.lower()]


def sheet_number(text):
    # Title blocks usually carry a sheet ID like A-601, A601 or A6.01; take the last one on the page.
    ids = re.findall(r"\b([A-Z]{1,2}-?\d{1,2}\.?\d{2})\b", text)
    return ids[-1] if ids else None


def pages_label(pages):
    return ", ".join(str(p + 1) for p in pages) if pages else ""


def scan_specs(texts, rules):
    toc = find_toc_pages(texts)
    toc_text = "\n".join(texts[i] for i in toc)
    body = [i for i in range(len(texts)) if i not in toc]
    rows = []
    for sec in rules["sections"]:
        pat = section_pattern(sec["number"])
        own_pat = own_page_pattern(sec["number"])
        in_toc = bool(pat.search(toc_text))
        own = [i for i in body if own_pat.search(texts[i])]
        mentioned = [i for i in body if pat.search(texts[i])]
        # Pages that mention the section stay listed either way, so nothing that used to be shown is hidden.
        pages = sorted(set(own) | set(mentioned))
        note = ""
        if own:
            status = "Found"
        elif in_toc:
            status = "Listed but missing"
            if mentioned:
                note = "Only referenced on these pages; the section's own pages aren't in the book."
        elif mentioned:
            status = "Referenced only"
            note = "Not in the table of contents and its own pages aren't in the book; only referenced on these pages."
        else:
            status = "Not in this set"
        rows.append({"item": f'{sec["number"]} {sec["name"]}', "source": "Specs",
                     "status": status, "pages": pages, "note": note})
    for label, words in rules["keywords"].items():
        pages = [i for i in body if any(w in texts[i].lower() for w in words)]
        rows.append({"item": f"Mentions: {label}", "source": "Specs",
                     "status": "Found" if pages else "No mentions", "pages": pages})
    return toc, rows


def scan_drawings(texts, rules):
    rows = []
    for word in rules["drawing_keywords"]:
        pages = [i for i, t in enumerate(texts) if word in t.lower()]
        sheets = [sheet_number(texts[i]) or f"p{i + 1}" for i in pages]
        rows.append({"item": f'Drawings: "{word}"', "source": "Drawings",
                     "status": "Found" if pages else "No mentions", "pages": pages,
                     "sheets": sheets})
    return rows


def no_text_pages(texts):
    return [i for i, t in enumerate(texts) if len(t.strip()) < 20]


def cover_page(rows):
    """One-page summary at the front of the packet."""
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    y = 740
    c.setFont("Helvetica-Bold", 14)
    c.drawString(54, y, "Bid scope packet")
    y -= 18
    c.setFont("Helvetica", 9)
    c.drawString(54, y, "Page numbers refer to the original PDFs. Every page listed is included after this one, bookmarked by item.")
    y -= 24
    for r in rows:
        if y < 60:
            c.showPage(); y = 740
        flagged = r["status"] in ("Listed but missing", "Referenced only")
        c.setFont("Helvetica-Bold" if flagged else "Helvetica", 9.5)
        c.drawString(54, y, r["item"][:62])
        c.drawString(360, y, r["status"])
        label = pages_label(r["pages"]) or "-"
        if flagged and r["pages"]:
            label = "ref. " + label  # pages that mention the section, not the section itself
        c.drawString(470, y, label[:24])
        y -= 15
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def build_packet(out_path, rows, spec_reader, dwg_reader):
    """Each matching page once, in document order, with a bookmark per item."""
    if not any(r["pages"] for r in rows):
        return 0
    writer = PdfWriter()
    for p in cover_page(rows).pages:
        writer.add_page(p)
    for reader, source in ((spec_reader, "Specs"), (dwg_reader, "Drawings")):
        if reader is None:
            continue
        mine = [r for r in rows if r["source"] == source and r["pages"]]
        where = {}
        for p in sorted({p for r in mine for p in r["pages"]}):
            where[p] = len(writer.pages)
            writer.add_page(reader.pages[p])
        for r in mine:
            refs = "referenced on " if r["status"] in ("Listed but missing", "Referenced only") else ""
            writer.add_outline_item(f'{r["item"]} ({refs}p. {pages_label(r["pages"])})', where[r["pages"][0]])
    with open(out_path, "wb") as f:
        writer.write(f)
    return len(writer.pages)


def write_reports(out, rows, warnings, packet_pages):
    with open(out / "summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Item", "Source", "Status", "Pages", "Sheets", "Note"])
        for r in rows:
            w.writerow([r["item"], r["source"], r["status"], pages_label(r["pages"]),
                        ", ".join(r.get("sheets", [])), r.get("note", "")])
    lines = ["# Bid scope summary", "",
             "| Item | Source | Status | Pages | Sheets | Note |", "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f'| {r["item"]} | {r["source"]} | {r["status"]} | {pages_label(r["pages"])} | '
                     f'{", ".join(r.get("sheets", []))} | {r.get("note", "")} |')
    lines.append("")
    missing = [r["item"] for r in rows if r["status"] == "Listed but missing"]
    if missing:
        lines.append("**Listed in the table of contents but not in the book (ask for these before bid day):** "
                     + "; ".join(missing))
        lines.append("")
    referenced = [r["item"] for r in rows if r["status"] == "Referenced only"]
    if referenced:
        lines.append("**Referenced in the book, but the section itself isn't here (check whether it's part of this bid):** "
                     + "; ".join(referenced))
        lines.append("")
    for wmsg in warnings:
        lines.append(f"**Check:** {wmsg}")
    lines.append("")
    lines.append(f"Scope packet: {packet_pages} pages in scope_packet.pdf, bookmarked by item."
                 if packet_pages else "No matching pages, so no scope packet was made.")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--specs", type=Path, help="spec book PDF")
    ap.add_argument("--drawings", type=Path, help="drawing set PDF")
    ap.add_argument("--rules", type=Path, default=HERE / "rules.json")
    ap.add_argument("--out", type=Path, default=Path("output"))
    args = ap.parse_args()
    if not args.specs and not args.drawings:
        ap.error("give --specs, --drawings, or both")

    rules = json.loads(args.rules.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    rows, warnings = [], []
    spec_reader = dwg_reader = None
    spec_rows, dwg_rows = [], []

    if args.specs:
        spec_reader, spec_texts = read_pages(args.specs)
        toc, spec_rows = scan_specs(spec_texts, rules)
        if not toc:
            warnings.append("No table of contents found in the first 15 spec pages, so missing sections can't be checked.")
        blank = no_text_pages(spec_texts)
        if blank:
            warnings.append(f"{len(blank)} spec page(s) have no text layer (scanned?) and were not searched: {pages_label(blank)}")
        rows += spec_rows
    if args.drawings:
        dwg_reader, dwg_texts = read_pages(args.drawings)
        dwg_rows = scan_drawings(dwg_texts, rules)
        blank = no_text_pages(dwg_texts)
        if blank:
            warnings.append(f"{len(blank)} drawing page(s) have no text layer (scanned?) and were not searched: {pages_label(blank)}")
        rows += dwg_rows

    packet_pages = build_packet(args.out / "scope_packet.pdf", rows, spec_reader, dwg_reader)
    print(write_reports(args.out, rows, warnings, packet_pages))


if __name__ == "__main__":
    main()
