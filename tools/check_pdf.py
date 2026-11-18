"""Inspect the generated PDF: text integrity, layout collisions and content.

Usage: .venv/Scripts/python tools/check_pdf.py
Renders a set of pages to screens/pdf/ for visual review.
"""
import re
import unicodedata
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "Life-in-the-UK-Study-Guide.pdf"
OUT = ROOT / "screens" / "pdf"

MOJIBAKE = ["\u00c2", "\u00e2\u0080", "\u00ef\u00bf\u00bd", "\ufffd", "\u00e3\u0082"]
EXPECTED = [
    "Life in the UK",
    "About this guide",
    "The Values and Principles of the UK",
    "What is the UK?",
    "A Long and Illustrious History",
    "A Modern, Thriving Society",
    "The UK Government, the Law and Your Role",
    "Quick check",
    "Practice exam A",
    "Practice exam B",
    "Score record",
]


def main():
    doc = pymupdf.open(PDF)
    print(f"pages: {doc.page_count} | size: {doc[0].rect.width:.0f}x{doc[0].rect.height:.0f}pt")

    pages_text = []
    issues = []
    for number, page in enumerate(doc, start=1):
        text = page.get_text("text")
        pages_text.append(text)
        if len(text.strip()) < 60:
            issues.append(f"page {number}: only {len(text.strip())} characters")
        for pattern in MOJIBAKE:
            if pattern in text:
                issues.append(f"page {number}: suspicious character {pattern!r}")
        text_blocks = []
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            x0, y0, x1, y1 = block["bbox"]
            if (x1 - x0) * (y1 - y0) > 400:  # skip decorative glyph blocks
                text_blocks.append(block["bbox"])
            if x1 > page.rect.width - 8 or x0 < 8:
                snippet = "".join(
                    span["text"] for line in block["lines"] for span in line["spans"]
                )[:40]
                issues.append(f"page {number}: text near edge ({x0:.0f}..{x1:.0f}) {snippet!r}")
            if y1 > page.rect.height - 4:
                issues.append(f"page {number}: text below bottom margin (y1={y1:.0f})")

        # Overlapping text blocks mean something is printed on top of something else.
        for i in range(len(text_blocks)):
            for j in range(i + 1, len(text_blocks)):
                a, b = pymupdf.Rect(text_blocks[i]), pymupdf.Rect(text_blocks[j])
                overlap = a & b
                if overlap.is_empty:
                    continue
                area = overlap.width * overlap.height
                smallest = min(a.width * a.height, b.width * b.height) or 1
                if area / smallest > 0.12:
                    issues.append(
                        f"page {number}: overlapping text blocks ({area:.0f}pt2, "
                        f"{area / smallest:.0%} of the smaller)"
                    )

    # Orphaned headings: a heading as the last thing on a page.
    for number, page in enumerate(doc, start=1):
        blocks = [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0]
        if not blocks:
            continue
        last = max(blocks, key=lambda b: b["bbox"][3])
        size = max(span["size"] for line in last["lines"] for span in line["spans"])
        if size >= 13.5 and last["bbox"][3] > page.rect.height - 90:
            heading = "".join(span["text"] for line in last["lines"] for span in line["spans"])
            issues.append(f"page {number}: heading at page bottom {heading[:50]!r}")

    joined = "\n".join(pages_text)

    print("\n-- content presence --")
    for needle in EXPECTED:
        print(f"  {'OK ' if needle in joined else 'MISS'} {needle}")

    print("\n-- counts --")
    print("  Quick check sections:", joined.count("Quick check\n"))
    print("  Practice exam headings:", len(re.findall(r"Practice exam [AB]", joined)))
    print("  Answer tables (Quick check answers):", joined.count("Quick check answers"))
    print("  Question numbers found:", len(re.findall(r"(?m)^\s*\d{1,2}\.\s", joined)))

    print("\n-- layout issues --")
    if issues:
        for issue in issues[:25]:
            print("  " + issue)
        print(f"  total issues: {len(issues)}")
    else:
        print("  none")

    # Render a spread of pages for visual review.
    OUT.mkdir(parents=True, exist_ok=True)
    targets = {1: "cover", 2: "about"}
    for label, title in [
        ("ch1", "The Values and Principles of the UK"),
        ("ch2", "What is the UK?"),
        ("ch3", "A Long and Illustrious History"),
        ("ch4", "A Modern, Thriving Society"),
        ("ch5", "The UK Government, the Law and Your Role"),
    ]:
        for index, page in enumerate(doc, start=1):
            if title in page.get_text("text") and index > 3:
                targets[index] = label
                targets[index + 1] = label + "-next"
                break
    for index, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if "Quick check answers" in text:
            targets[index] = "answers"
            break
    for index, page in enumerate(doc, start=1):
        if "Practice exam A" in page.get_text("text"):
            targets[index] = "examA"
            break
    targets[doc.page_count] = "last"

    for number in sorted(targets):
        if not 1 <= number <= doc.page_count:
            continue
        pix = doc[number - 1].get_pixmap(dpi=105)
        path = OUT / f"p{number:02d}-{targets[number]}.png"
        pix.save(path)

    print(f"\nrendered {len(targets)} pages to {OUT}")


if __name__ == "__main__":
    main()
