"""Make a small, made-up bid set to test scope_finder (no real project data).

specs.pdf   : cover, table of contents, and a few sections. 08 33 13 is listed in the
              table of contents but left out of the book on purpose. The elevator smoke
              curtain is buried in the elevator section, not a door section.
drawings.pdf: cover, floor plan, door schedule sheet, and one image-only "scanned" sheet.
"""
from pathlib import Path

from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
PROJECT = "SAMPLE WAREHOUSE (fictional) - BID SET"


def page(c, lines, footer=None, size=11):
    w, h = c._pagesize
    y = h - 72
    for line in lines:
        c.setFont("Helvetica-Bold" if line.isupper() else "Helvetica", size)
        c.drawString(72, y, line)
        y -= size + 7
    if footer:
        c.setFont("Helvetica", 9)
        c.drawCentredString(w / 2, 36, footer)
    c.showPage()


def specs():
    c = canvas.Canvas(str(HERE / "specs.pdf"), pagesize=letter)
    page(c, [PROJECT, "PROJECT MANUAL", "VOLUME 1 - SPECIFICATIONS"])
    page(c, ["TABLE OF CONTENTS", "",
             "DIVISION 08 - OPENINGS",
             "08 11 13  Hollow Metal Doors and Frames",
             "08 33 13  Coiling Counter Doors",
             "08 33 23  Overhead Coiling Doors",
             "08 36 13  Sectional Doors",
             "DIVISION 09 - FINISHES",
             "09 91 23  Interior Painting",
             "DIVISION 11 - EQUIPMENT",
             "11 13 19  Stationary Loading Dock Equipment",
             "DIVISION 14 - CONVEYING EQUIPMENT",
             "14 21 00  Electric Traction Elevators"], footer="TABLE OF CONTENTS - 1")
    page(c, ["SECTION 08 11 13 - HOLLOW METAL DOORS AND FRAMES", "PART 1 - GENERAL",
             "Steel doors and frames as scheduled."], footer="08 11 13 - 1")
    for n in (1, 2, 3):
        page(c, ["SECTION 08 33 23 - OVERHEAD COILING DOORS" if n == 1 else "OVERHEAD COILING DOORS (CONTINUED)",
                 "Insulated overhead coiling doors, motor operated, as scheduled on the drawings.",
                 "Curtain: interlocking flat slats, galvanized steel.",
                 "Fire-rated overhead coiling door FD-2: 90 minute rating, listed assembly."],
             footer=f"08 33 23 - {n}")
    for n in (1, 2):
        page(c, ["SECTION 08 36 13 - SECTIONAL DOORS" if n == 1 else "SECTIONAL DOORS (CONTINUED)",
                 "Insulated steel sectional doors, electric operator, as scheduled."],
             footer=f"08 36 13 - {n}")
    page(c, ["SECTION 09 91 23 - INTERIOR PAINTING", "Paint exposed steel. Do not paint dock seal fabric."],
         footer="09 91 23 - 1")
    for n in (1, 2):
        page(c, ["SECTION 11 13 19 - STATIONARY LOADING DOCK EQUIPMENT" if n == 1 else "LOADING DOCK EQUIPMENT (CONTINUED)",
                 "Hydraulic pit-style dock leveler, 6'-0\" x 8'-0\", quantity as indicated.",
                 "Dock seals at each dock door."], footer=f"11 13 19 - {n}")
    for n in (1, 2):
        page(c, ["SECTION 14 21 00 - ELECTRIC TRACTION ELEVATORS" if n == 1 else "ELEVATORS (CONTINUED)",
                 "Provide car and hoistway equipment as specified.",
                 "Provide an elevator smoke curtain at each elevator door opening on floors 2 and 3." if n == 2
                 else "Fixtures: stainless steel."], footer=f"14 21 00 - {n}")
    c.save()


def drawings():
    c = canvas.Canvas(str(HERE / "drawings.pdf"), pagesize=landscape(letter))
    page(c, [PROJECT, "SHEET INDEX", "G-001 COVER", "A-101 FIRST FLOOR PLAN", "A-601 DOOR SCHEDULE",
             "A-602 DOOR DETAILS (SCANNED)"], footer="G-001")
    page(c, ["FIRST FLOOR PLAN", "Dock doors OH-1 (4) along north wall. Sectional doors SD-1 (2) at shop.",
             "Fire door FD-2 at storage room. Dock leveler at each OH-1 position."], footer="A-101")
    page(c, ["DOOR SCHEDULE",
             "MARK  TYPE                          SIZE            QTY  RATING   OPERATION",
             "OH-1  Overhead coiling door         12'-0\" x 14'-0\"  4    -        Motor",
             "FD-2  Rolling fire door (coiling)   8'-0\" x 8'-0\"    1    90 MIN   Motor",
             "SD-1  Sectional door                10'-0\" x 10'-0\"  2    -        Motor",
             "See specification sections 08 33 23 and 08 36 13."], footer="A-601", size=10)
    # an image-only page: shapes, no text layer, like a scanned sheet
    c.rect(72, 72, 500, 380)
    c.line(72, 72, 572, 452)
    c.showPage()
    c.save()


if __name__ == "__main__":
    specs()
    drawings()
    print("wrote sample/specs.pdf and sample/drawings.pdf")
