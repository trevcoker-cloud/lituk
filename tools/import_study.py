"""Import the five study chapters into study.js.

Each chapter page on lifeintheuktestweb.co.uk holds the revision notes for one
chapter of the handbook. This script extracts the article body (headings,
paragraphs and lists) into readable blocks for the study page.

Usage: python tools/import_study.py
"""
import html as html_mod
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "study.js"

CHAPTERS = [
    (1, "The Values and Principles of the UK", "the-values-and-principles-of-the-uk"),
    (2, "What is the UK?", "what-is-the-uk"),
    (3, "A Long and Illustrious History", "a-long-and-illustrious-history"),
    (4, "A Modern, Thriving Society", "a-modern-thriving-society"),
    (5, "The UK Government, the Law and Your Role", "the-uk-government-the-law-and-your-role"),
]

TAG = re.compile(r"<[^>]+>")
NOISE = ("Advertisement", "iiq_pixel", "TEST YOUR KNOWLEDGE", "GO TO CHAPTER")


def clean(fragment):
    fragment = re.sub(r"<br\s*/?>", " ", fragment)
    fragment = TAG.sub(" ", fragment)
    fragment = html_mod.unescape(fragment).replace("\xa0", " ")
    fragment = re.sub(r"\s+", " ", fragment).strip()
    fragment = re.sub(r"\s+([,.;:!?])", r"\1", fragment)
    return fragment.strip()


def fetch(slug):
    url = "https://lifeintheuktestweb.co.uk/" + slug + "/"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; lituk-importer/1.0)"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read().decode("utf-8", "replace")


class Article(HTMLParser):
    """Collect headings, paragraphs and list items from the article body."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.buffer = []
        self.mode = None
        self.list_depth = 0
        self.list_items = None
        self.skip = 0

    # -- helpers
    def commit_paragraph(self):
        if self.mode == ("p",):
            value = clean("".join(self.buffer))
            if value and not value.startswith(NOISE):
                self.blocks.append({"t": "p", "x": value})
        self.buffer = []
        self.mode = None

    def commit_heading(self):
        if self.mode and self.mode[0] == "h":
            value = clean("".join(self.buffer))
            if value and not value.startswith(NOISE):
                self.blocks.append({"t": "h2" if self.mode[1] <= 2 else "h3", "x": value})
        self.buffer = []
        self.mode = None

    def commit_item(self):
        if self.mode == ("li",) and self.list_items is not None:
            value = clean("".join(self.buffer))
            if value and not value.startswith(NOISE):
                self.list_items.append(value)
        self.buffer = []
        self.mode = None

    # -- parser hooks
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
            return
        if self.skip:
            return

        if tag in ("h2", "h3", "h4"):
            self.commit_paragraph()
            self.mode = ("h", int(tag[1]))
            self.buffer = []
        elif tag == "p":
            if self.mode is None and self.list_depth == 0:
                self.mode = ("p",)
                self.buffer = []
        elif tag in ("ul", "ol"):
            if self.mode == ("p",):
                self.commit_paragraph()
            self.list_depth += 1
            if self.list_depth == 1:
                self.list_items = []
        elif tag == "li":
            if self.mode == ("p",):
                self.commit_paragraph()
            self.commit_heading()
            self.mode = ("li",)
            self.buffer = []
        elif tag == "br" and self.mode:
            self.buffer.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return

        if tag in ("h2", "h3", "h4"):
            self.commit_heading()
        elif tag == "p":
            if self.mode == ("p",):
                self.commit_paragraph()
        elif tag == "li":
            self.commit_item()
        elif tag in ("ul", "ol"):
            if self.list_depth:
                self.list_depth -= 1
            if self.list_depth == 0 and self.list_items is not None:
                if self.list_items:
                    self.blocks.append({"t": "ul", "x": self.list_items})
                self.list_items = None

    def handle_data(self, data):
        if self.skip or not self.mode:
            return
        self.buffer.append(data)


BULLETS = ("\u2022", "\u00b7", "\u25aa", "\u25cf")


def postprocess(blocks):
    """Turn bullet-style paragraphs into lists and drop repeated headings."""
    out = []
    pending_bullets = []
    seen_headings = set()

    def flush_bullets():
        if pending_bullets:
            out.append({"t": "ul", "x": pending_bullets[:]})
            pending_bullets.clear()

    for block in blocks:
        text = block["x"] if isinstance(block["x"], str) else ""
        stripped = text.lstrip("".join(BULLETS) + " -\u2013\t")
        if block["t"] == "p" and text[:1] in BULLETS and stripped:
            pending_bullets.append(stripped.strip())
            continue

        flush_bullets()

        if block["t"] in ("h2", "h3"):
            key = block["x"].strip().lower()
            if key in seen_headings:
                continue
            seen_headings.add(key)

        out.append(block)

    flush_bullets()
    return out


def parse(page):
    start = page.find("elementor-widget-theme-post-content")
    if start < 0:
        raise ValueError("article container not found")
    end = page.find("Support this project", start)
    body = page[start:end if end > start else start + 400000]

    collector = Article()
    collector.feed(body)
    collector.commit_item()
    collector.commit_paragraph()

    blocks = []
    for block in collector.blocks:
        if blocks and blocks[-1] == block:
            continue
        blocks.append(block)
    return postprocess(blocks)


def summarise(blocks):
    for block in blocks:
        if block["t"] == "p" and len(block["x"]) > 80:
            text = block["x"]
            return text if len(text) <= 210 else text[:207].rsplit(" ", 1)[0] + "…"
    return ""


def main():
    chapters = []
    for number, title, slug in CHAPTERS:
        page = fetch(slug)
        blocks = parse(page)
        chapters.append(
            {
                "number": number,
                "id": "chapter-" + str(number),
                "title": title,
                "summary": summarise(blocks),
                "blocks": blocks,
            }
        )
        print(f"chapter {number}: {len(blocks)} blocks")

    payload = "window.LITUK_STUDY = " + json.dumps(
        chapters, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    OUT.write_text(payload, encoding="utf-8")
    total = sum(len(chapter["blocks"]) for chapter in chapters)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB, {total} blocks)")


if __name__ == "__main__":
    main()
