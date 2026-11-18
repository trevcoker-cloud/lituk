"""Build the printable study guide from study.js and tests.js.

Produces print/guide.html, designed for A4, which is then rendered to PDF with
headless Chrome (see tools/print_guide.sh).

Usage: python tools/build_guide.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "print"
OUT = OUT_DIR / "guide.html"

LETTERS = "ABCDEFGH"
PASS_MARK = 18
QUESTIONS_PER_CHECK = 10
EXAMS = ["test-1", "test-2"]


def load(name):
    raw = (ROOT / name).read_text(encoding="utf-8")
    body = raw.split("=", 1)[1].strip().rstrip(";")
    return json.loads(body)


TYPO_FIXES = (
    ("Life in the Uk test", "Life in the UK test"),
    ("usually taken is English", "usually taken in English"),
)


def esc(text):
    for wrong, right in TYPO_FIXES:
        text = text.replace(wrong, right)
    text = text.replace("\ufeff", "").replace("\u200b", "").replace("\xa0", " ")
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\(\s+", "(", text)
    return html.escape(text, quote=False)


def letters(answer):
    return ", ".join(LETTERS[i] for i in answer)


def question_block(question, number):
    options = []
    for index, option in enumerate(question["o"]):
        options.append(
            '<li><span class="tick"></span>'
            '<span class="letter">' + LETTERS[index] + "</span>"
            '<span class="label">' + esc(option) + "</span></li>"
        )
    hint = ""
    if len(question["a"]) > 1:
        hint = '<span class="hint">Choose ' + str(len(question["a"])) + " answers</span>"
    return (
        '<li class="question">'
        '<p class="q-text"><span class="q-num">' + str(number) + ".</span> "
        + esc(question["q"]) + hint + "</p>"
        '<ul class="q-options">' + "".join(options) + "</ul>"
        "</li>"
    )


def answer_rows(questions, start=1):
    rows = []
    for index, question in enumerate(questions):
        explain = question.get("e", "")
        rows.append(
            "<tr><td class='num'>" + str(start + index) + "</td>"
            "<td class='ans'>" + letters(question["a"]) + "</td>"
            "<td>" + esc(explain) + "</td></tr>"
        )
    return "".join(rows)


def quick_check(pool, count):
    if len(pool) <= count:
        return pool
    step = (len(pool) - 1) / (count - 1)
    chosen = []
    for index in range(count):
        question = pool[round(index * step)]
        if question not in chosen:
            chosen.append(question)
    return chosen


def chapter_pool(tests, group):
    seen = set()
    pool = []
    for test in tests:
        if test["group"] != group:
            continue
        for question in test["questions"]:
            key = question["q"].lower()
            if key in seen:
                continue
            seen.add(key)
            pool.append(question)
    return pool


def build():
    study = load("study.js")
    tests = load("tests.js")
    groups = {
        1: "Chapters 1\u20132",
        2: "Chapters 1\u20132",
        3: "Chapter 3",
        4: "Chapter 4",
        5: "Chapter 5",
    }

    total_checks = 0
    chapters_html = []
    for chapter in study:
        pool = chapter_pool(tests, groups[chapter["number"]])
        checks = quick_check(pool, QUESTIONS_PER_CHECK)
        total_checks += len(checks)

        notes = []
        # The stored summary is truncated for cards, so print the full opening
        # paragraph as the chapter lead instead and leave it out of the notes.
        blocks = chapter["blocks"]
        lead = ""
        if blocks and blocks[0]["t"] == "p":
            lead = '<p class="chapter-summary">' + esc(blocks[0]["x"]) + "</p>"
            blocks = blocks[1:]
        for block in blocks:
            if block["t"] == "h2":
                notes.append("<h2>" + esc(block["x"]) + "</h2>")
            elif block["t"] == "h3":
                notes.append("<h3>" + esc(block["x"]) + "</h3>")
            elif block["t"] == "ul":
                items = "".join("<li>" + esc(item) + "</li>" for item in block["x"])
                notes.append("<ul>" + items + "</ul>")
            else:
                notes.append("<p>" + esc(block["x"]) + "</p>")

        chapters_html.append(
            '<section class="chapter">'
            '<p class="chapter-label">Chapter ' + str(chapter["number"]) + "</p>"
            "<h1>" + esc(chapter["title"]) + "</h1>"
            + lead
            + "".join(notes) +
            '<section class="check">'
            "<h2>Quick check</h2>"
            '<p class="lead">Ten questions drawn from this chapter. Circle your answers, then check '
            "them at the end of the section.</p>"
            '<ol class="quiz">' + "".join(question_block(q, i + 1) for i, q in enumerate(checks)) + "</ol>"
            '<div class="answer-box">'
            '<p class="answer-title">Quick check answers</p>'
            '<table class="answer-table"><tbody>' + answer_rows(checks) + "</tbody></table>"
            "</div>"
            "</section>"
            "</section>"
        )

    exams_html = []
    for exam_index, exam_id in enumerate(EXAMS):
        test = next(t for t in tests if t["id"] == exam_id)
        exams_html.append(
            '<section class="exam">'
            '<p class="chapter-label">Practice exam ' + "AB"[exam_index] + "</p>"
            "<h1>" + esc(test["name"]) + "</h1>"
            '<p class="chapter-summary">Twenty-four questions. Allow forty-five minutes. '
            "You need eighteen correct to pass.</p>"
            '<ol class="quiz">'
            + "".join(question_block(q, i + 1) for i, q in enumerate(test["questions"]))
            + "</ol></section>"
        )

    keys_html = []
    for exam_index, exam_id in enumerate(EXAMS):
        test = next(t for t in tests if t["id"] == exam_id)
        keys_html.append(
            '<section class="key">'
            '<h2>Practice exam ' + "AB"[exam_index] + " \u2014 answers</h2>"
            '<table class="answer-table"><tbody>'
            + answer_rows(test["questions"]) +
            "</tbody></table></section>"
        )

    badge = ROOT / "brand-badge.svg"
    badge_svg = badge.read_text(encoding="utf-8").replace('width="600" height="600" ', "", 1)

    doc = """<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<title>Life in the UK \u2014 Complete Study Guide</title>
<style>
  @page { size: A4; margin: 16mm 15mm 18mm; }
  :root { --ink: #12213a; --soft: #55637a; --line: #d8cfc0; --red: #c8102e; --green: #1d6b45; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: 10.5pt; line-height: 1.5; color: #1a2436; }
  h1, h2, h3 { font-family: Georgia, serif; color: var(--ink); }
  h1 { font-size: 26pt; line-height: 1.1; margin: 0 0 10pt; }
  h2 { font-size: 14.5pt; margin: 18pt 0 6pt; break-after: avoid-page; }
  h3 { font-size: 11.5pt; margin: 13pt 0 4pt; break-after: avoid-page; }
  p, li { orphans: 2; widows: 2; }
  .answer-table tr { break-inside: avoid; }
  p { margin: 0 0 7pt; }
  ul { margin: 0 0 9pt; padding-left: 16pt; }
  li { margin-bottom: 3pt; }

  .cover { height: 245mm; display: flex; flex-direction: column; justify-content: space-between; break-after: page; }
  .cover-top { display: flex; align-items: center; gap: 14pt; }
  .cover-top .badge-mark { display: block; flex: none; }
  .cover-top svg { width: 58pt; height: 58pt; display: block; }
  .org { font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 8.5pt; letter-spacing: .18em; text-transform: uppercase; color: var(--soft); }
  .cover-main { margin-top: 40pt; }
  .cover-kicker { font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 9pt; letter-spacing: .22em; text-transform: uppercase; color: var(--red); margin-bottom: 12pt; }
  .cover h1 { font-size: 46pt; line-height: 1.02; }
  .cover h1 em { font-style: normal; color: var(--red); }
  .cover-sub { font-size: 14pt; color: var(--soft); margin-top: 14pt; max-width: 130mm; }
  .cover-rule { border: 0; border-top: 2px solid var(--ink); margin: 26pt 0 14pt; width: 60mm; }
  .cover-meta { font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 9pt; letter-spacing: .08em; color: var(--soft); }
  .cover-foot { font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 8.5pt; color: var(--soft); border-top: 1px solid var(--line); padding-top: 8pt; display: flex; justify-content: space-between; }

  .frontmatter { break-after: page; }
  .facts { display: flex; gap: 10pt; margin: 14pt 0 20pt; }
  .fact { flex: 1; border: 1px solid var(--line); border-radius: 4pt; padding: 8pt 10pt; }
  .fact strong { display: block; font-size: 20pt; line-height: 1.1; }
  .fact span { font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 8pt; letter-spacing: .08em; text-transform: uppercase; color: var(--soft); }
  .toc { columns: 2; column-gap: 16mm; font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 9.5pt; }
  .toc p { margin: 0 0 5pt; break-inside: avoid; }
  .toc .toc-head { font-weight: 700; color: var(--red); letter-spacing: .12em; text-transform: uppercase; font-size: 8pt; margin-top: 8pt; }

  .chapter, .exam { break-before: page; }
  .chapter-label { font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 9pt; letter-spacing: .2em; text-transform: uppercase; color: var(--red); margin-bottom: 4pt; }
  .chapter h1 { font-size: 24pt; margin-bottom: 8pt; }
  .chapter-summary { color: var(--soft); font-size: 10.5pt; max-width: 150mm; margin-bottom: 12pt; }

  .check { break-before: page; margin-top: 4pt; }
  .check h2 { font-size: 18pt; margin-top: 0; }
  .lead { color: var(--soft); font-size: 9.5pt; }

  .quiz { list-style: none; margin: 10pt 0 0; padding: 0; }
  .question { break-inside: avoid; margin-bottom: 12pt; padding-bottom: 4pt; }
  .q-text { font-size: 10.5pt; margin-bottom: 5pt; }
  .q-num { font-weight: 700; color: var(--red); }
  .hint { display: block; font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 8pt; letter-spacing: .08em; text-transform: uppercase; color: var(--soft); margin-top: 2pt; }
  .q-options { list-style: none; margin: 0; padding: 0; columns: 2; column-gap: 10mm; }
  .q-options li { font-size: 9.8pt; margin-bottom: 3pt; break-inside: avoid; display: flex; gap: 4pt; align-items: baseline; }
  .tick { display: inline-block; width: 7pt; height: 7pt; border: 1px solid #98a1b1; flex: none; margin-right: 2pt; }
  .letter { font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-weight: 700; font-size: 8pt; color: var(--soft); min-width: 9pt; }
  .label { flex: 1; }

  .answer-box { break-before: page; border-top: 2px solid var(--ink); padding-top: 10pt; }
  .answer-title { font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 8.5pt; letter-spacing: .16em; text-transform: uppercase; color: var(--red); margin-bottom: 8pt; }
  .answer-table { width: 100%; border-collapse: collapse; font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 8.5pt; color: #2b3a52; }
  .answer-table td { border-bottom: 1px solid #e8e1d4; padding: 3.5pt 4pt; vertical-align: top; }
  .answer-table td.num { width: 12pt; color: var(--soft); }
  .answer-table td.ans { width: 26pt; font-weight: 700; color: var(--green); white-space: nowrap; }
  .key { break-before: page; }
  .key h2 { margin-top: 0; }

  .record-table { width: 100%; border-collapse: collapse; margin-top: 8pt; font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 9pt; }
  .record-table th, .record-table td { border: 1px solid var(--line); padding: 6pt 8pt; text-align: left; }
  .record-table th { background: #f4efe5; font-size: 8pt; letter-spacing: .08em; text-transform: uppercase; color: var(--soft); }
  .record-table td { height: 14pt; }

  @media screen {
    html { background: #efe9dd; }
    body { max-width: 210mm; margin: 0 auto; padding: 16mm 15mm 20mm; background: #fff; box-shadow: 0 0 0 1px #e2dacb; }
    footer { display: none; }
  }

</style>
</head>
<body>

<section class="cover">
  <div class="cover-top">
    <span class="badge-mark">""" + badge_svg + """</span>
    <div>
      <p class="org">Sneinton Community Education</p>
      <p class="org" style="letter-spacing:.06em;text-transform:none;font-size:8pt;">Study &amp; practice resources</p>
    </div>
  </div>

  <div class="cover-main">
    <p class="cover-kicker">2026 edition \u00b7 3rd edition handbook</p>
    <h1>Life in the <em>UK</em><br>study guide</h1>
    <p class="cover-sub">All five chapters of <em>Life in the United Kingdom: A Guide for New Residents</em>, with chapter checks and two full practice exams.</p>
    <hr class="cover-rule">
    <p class="cover-meta">5 chapters \u00b7 """ + str(total_checks) + """ chapter questions \u00b7 2 practice exams \u00b7 48 exam questions</p>
  </div>

  <p class="cover-foot"><span>24 questions \u00b7 45 minutes \u00b7 18 to pass</span><span>Not affiliated with GOV.UK</span></p>
</section>

<section class="frontmatter">
  <h1 style="font-size:22pt;">About this guide</h1>
  <p>This guide collects the study material for the Life in the UK test in one printable book. Each chapter follows the handbook's own order: read the notes, then answer the ten questions at the end of the chapter and check yourself against the answers that follow. When all five chapters are done, sit the two practice exams under timed conditions.</p>

  <div class="facts">
    <div class="fact"><strong>24</strong><span>questions per test</span></div>
    <div class="fact"><strong>45</strong><span>minutes</span></div>
    <div class="fact"><strong>18/24</strong><span>to pass \u00b7 75%</span></div>
    <div class="fact"><strong>5</strong><span>chapters</span></div>
  </div>

  <h2>What the test is</h2>
  <p>The Life in the UK test is a 24-question multiple-choice test taken at an approved test centre. Questions cover the whole handbook, and several questions ask you to select more than one answer — those only count when every correct option is chosen and nothing else. You need 18 out of 24 (75%) to pass.</p>

  <h2>How to use this book</h2>
  <ul>
    <li><strong>Week 1–2:</strong> Chapter 1 and Chapter 2, then their quick checks.</li>
    <li><strong>Week 3–4:</strong> Chapter 3 (history) — the longest chapter. Read a section, then answer the quick check in one sitting.</li>
    <li><strong>Week 5:</strong> Chapter 4 (society, culture, sport, traditions).</li>
    <li><strong>Week 6:</strong> Chapter 5 (government, law, your role), then Practice exam A.</li>
    <li><strong>Final week:</strong> Practice exam B under timed conditions, then re-read the answer notes for anything you missed.</li>
  </ul>

  <h2>Contents</h2>
  <div class="toc">
    <p class="toc-head">Study material</p>
""" + "".join(
        '<p><strong>Chapter ' + str(ch["number"]) + "</strong> \u00b7 " + esc(ch["title"]) + "</p>"
        for ch in study
    ) + """
    <p class="toc-head">Practice</p>
    <p><strong>Practice exam A</strong> \u00b7 24 questions, 45 minutes</p>
    <p><strong>Practice exam B</strong> \u00b7 24 questions, 45 minutes</p>
    <p><strong>Answers</strong> \u00b7 all practice exams</p>
    <p class="toc-head">Reference</p>
    <p><strong>Score record</strong> \u00b7 track your practice</p>
  </div>

  <p style="margin-top:14pt;color:var(--soft);font-size:9.5pt;">The companion website holds the full bank of 73 practice papers, with instant scoring and a shareable result. This book contains the complete notes, the chapter checks and two timed practice exams.</p>
</section>

""" + "\n".join(chapters_html) + """

""" + "\n".join(exams_html) + """

""" + "\n".join(keys_html) + """

<section class="chapter">
  <h1>Score record</h1>
  <p>Write down every practice attempt — the score, the date and the questions you got wrong. Revisit those notes before the next attempt.</p>
  <table class="record-table">
    <thead><tr><th>Date</th><th>Paper</th><th>Score</th><th>Notes</th></tr></thead>
    <tbody>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
      <tr><td></td><td></td><td></td><td></td></tr>
    </tbody>
  </table>
  <p style="margin-top:14pt;font-size:9pt;color:var(--soft);">Study material follows <em>Life in the United Kingdom: A Guide for New Residents</em> (3rd edition). Practice questions and explanations are taken from the question bank published on lifeintheuktestweb.co.uk. This is an independent study aid and is not affiliated with GOV.UK.</p>
</section>

</body>
</html>
"""

    OUT_DIR.mkdir(exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")
    print("badge exists:", badge.exists())
    print("chapters:", len(study), "questions per chapter:", QUESTIONS_PER_CHECK, "exams:", len(EXAMS))


if __name__ == "__main__":
    build()
