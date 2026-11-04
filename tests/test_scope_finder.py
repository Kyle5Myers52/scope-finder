"""Checks for how scope_finder decides whether a spec section is in the book.

Run with:  python tests/test_scope_finder.py   (or: python -m pytest tests)
Each test builds a tiny spec book as a list of page texts, the same shape read_pages returns.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scope_finder as sf  # noqa: E402

RULES = json.loads((ROOT / "rules.json").read_text())
TOC = "TABLE OF CONTENTS\n08 33 13  Coiling Counter Doors\n08 33 23  Overhead Coiling Doors\n08 71 00  Door Hardware"


def status_of(texts, number):
    _, rows = sf.scan_specs(texts, RULES)
    row = next(r for r in rows if r["item"].startswith(number))
    return row["status"], row["pages"]


def test_cross_reference_does_not_count_as_found():
    # 08 33 13 is in the table of contents, absent from the book, and mentioned by another section.
    texts = ["COVER", TOC,
             "SECTION 08 71 00 - DOOR HARDWARE\nCoordinate with Section 08 33 13.\n08 71 00 - 1"]
    status, pages = status_of(texts, "08 33 13")
    assert status == "Listed but missing", status
    assert pages == [2], pages  # the referencing page is still shown, so nothing is hidden


def test_listed_and_never_mentioned_is_missing():
    texts = ["COVER", TOC, "SECTION 08 71 00 - DOOR HARDWARE\n08 71 00 - 1"]
    assert status_of(texts, "08 33 13") == ("Listed but missing", [])


def test_heading_and_footer_is_found():
    texts = ["COVER", TOC,
             "SECTION 08 33 23 - OVERHEAD COILING DOORS\nPART 1 - GENERAL\n08 33 23 - 1",
             "OVERHEAD COILING DOORS\nCurtain: interlocking slats.\n08 33 23 - 2"]
    assert status_of(texts, "08 33 23") == ("Found", [2, 3])


def test_footer_alone_is_found():
    texts = ["COVER", TOC, "Curtain: interlocking slats.\nOVERHEAD COILING DOORS 08 33 23 - 4"]
    assert status_of(texts, "08 33 23")[0] == "Found"


def test_title_case_heading_is_found():
    texts = ["COVER", TOC, "Section 08 33 23 - Overhead Coiling Doors\nPart 1 - General"]
    assert status_of(texts, "08 33 23")[0] == "Found"


def test_end_of_section_line_is_found():
    texts = ["COVER", TOC, "Clean up the work area.\nEND OF SECTION 08 33 23"]
    assert status_of(texts, "08 33 23")[0] == "Found"


def test_extra_spaces_in_section_number():
    texts = ["COVER", TOC, "SECTION 08  33  23 - OVERHEAD COILING DOORS"]
    assert status_of(texts, "08 33 23")[0] == "Found"


def test_reference_wrapped_to_start_of_line_is_not_found():
    texts = ["COVER", TOC,
             "SECTION 08 71 00 - DOOR HARDWARE\nFrames at counter doors: coordinate with\nSection 08 33 13 for sizes.\n08 71 00 - 2"]
    assert status_of(texts, "08 33 13")[0] == "Listed but missing"


def test_reference_with_no_toc_is_referenced_only():
    texts = ["COVER", "SECTION 08 71 00 - DOOR HARDWARE\nCoordinate with Section 08 33 13.\n08 71 00 - 1"]
    assert status_of(texts, "08 33 13") == ("Referenced only", [1])


def test_absent_everywhere_is_not_in_this_set():
    texts = ["COVER", TOC, "SECTION 08 71 00 - DOOR HARDWARE\n08 71 00 - 1"]
    assert status_of(texts, "11 13 19") == ("Not in this set", [])


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"pass  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(tests) - failed} of {len(tests)} passed")
    sys.exit(1 if failed else 0)
