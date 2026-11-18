"""Import the Life in the UK practice tests into tests.js.

Scrapes every /test.../ page linked from /tests/ and reads the answer key that
each page embeds (the `solution` object used by its quiz script), so the
imported answers are the site's own, not guesses.

Usage: python tools/import_tests.py
"""
import concurrent.futures
import html as html_mod
import json
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://lifeintheuktestweb.co.uk/"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests.js"

SLUGS = [f"test-{n}" for n in range(1, 41)]
SLUGS += ["test-1-2"]
SLUGS += [f"test-3-{n}" for n in range(1, 11)]
SLUGS += [f"test-4-{n}" for n in range(1, 13)]
SLUGS += [f"test-5-{n}" for n in range(1, 11)]

TAG = re.compile(r"<[^>]+>")
EMPTY_LABELS = []


def text(fragment):
    fragment = re.sub(r"<br\s*/?>", " ", fragment)
    fragment = TAG.sub(" ", fragment)
    fragment = html_mod.unescape(fragment).replace("\xa0", " ")
    fragment = re.sub(r"\s+", " ", fragment).strip()
    fragment = re.sub(r"\s+([,.;:!?])", r"\1", fragment)
    return fragment.strip()


def fetch(slug, attempts=5):
    url = BASE + slug + "/"
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (compatible; lituk-importer/1.0)"}
            )
            with urllib.request.urlopen(request, timeout=40) as response:
                return response.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 - retry any transport failure
            last = exc
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(str(last))


def display_name(slug):
    return "Test " + slug[len("test-"):].replace("-", ".")


def group_name(slug):
    if re.fullmatch(r"test-\d+", slug):
        return "Full tests"
    if slug == "test-1-2":
        return "Chapters 1–2"
    return "Chapter " + slug.split("-")[1]


def extract_solution(page):
    """Read the `const solution = {...}` object that each page embeds."""
    anchor = page.find("const solution")
    if anchor < 0:
        raise ValueError("no answer key")
    start = page.find("{", anchor)
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(page)):
        char = page[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(page[start:index + 1])
    raise ValueError("unterminated answer key")


def parse(slug, page):
    solution = extract_solution(page)

    blocks = page.split('<div class="container_question" data-id_question="')[1:]
    if not blocks:
        raise ValueError(f"{slug}: no questions found")

    questions = []
    for block in blocks:
        # The final question block runs to the end of the page, so stop at the
        # navigation/script markup that follows the last question.
        for stop in ('id="container_buttons', "(adsbygoogle", "const time ="):
            block = block.split(stop, 1)[0]
        block = re.sub(r"<[^>]*$", "", block)
        qid = block.split('"', 1)[0]
        question_match = re.search(r'<div class="question">(.*?)</div>', block, re.S)
        if not question_match:
            continue
        question = text(question_match.group(1))

        answer_part = block.split('class="container_answer"', 1)
        segment = answer_part[1] if len(answer_part) > 1 else block
        options = []
        for option_match in re.finditer(
            r'data-id_answer="(r\d+)"[^>]*>(.*?)</label>', segment, re.S
        ):
            options.append((option_match.group(1), text(option_match.group(2))))

        labels = [label for _, label in options]
        positions = {key: index for index, (key, _) in enumerate(options)}

        raw_answer = solution.get(qid, "")
        keys = [part for part in raw_answer.split(",") if part]
        answer = sorted(positions[key] for key in keys if key in positions)

        explanation = ""
        explanation_match = re.search(
            r'<div class="container_explication"[^>]*>(.*)$', block, re.S
        )
        if explanation_match:
            explanation = text(
                explanation_match.group(1).replace(
                    '<div class="container_response_correct_incorrect"></div>', ""
                )
            )

        if not question or len(labels) < 2:
            continue
        if not answer or len(answer) != len(keys):
            raise ValueError(f"{slug}/{qid}: answer key {raw_answer!r} does not match options")
        if any(not label for label in labels):
            EMPTY_LABELS.append(f"{slug}/{qid}")

        questions.append(
            {"q": question, "o": labels, "a": answer, "e": explanation}
        )

    return questions


def main():
    tests = []
    failures = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, slug): slug for slug in SLUGS}
        pages = {}
        for future in concurrent.futures.as_completed(futures):
            slug = futures[future]
            try:
                pages[slug] = future.result()
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{slug}: {exc}")

    for slug in SLUGS:
        if slug not in pages:
            continue
        try:
            questions = parse(slug, pages[slug])
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{slug}: {exc}")
            continue
        tests.append(
            {
                "id": slug,
                "name": display_name(slug),
                "group": group_name(slug),
                "questions": questions,
            }
        )

    total = sum(len(test["questions"]) for test in tests)
    payload = "window.LITUK_TESTS = " + json.dumps(
        tests, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    OUT.write_text(payload, encoding="utf-8")

    counts = sorted({len(test["questions"]) for test in tests})
    print(f"tests: {len(tests)}  questions: {total}  counts: {counts}")
    print(f"empty option labels: {len(EMPTY_LABELS)}")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)


if __name__ == "__main__":
    main()
