#!/usr/bin/env bash
# Build print/guide.html and render it to Life-in-the-UK-Study-Guide.pdf.
#
#   bash tools/print_guide.sh
#
# Uses the locally installed Chrome or Edge in headless mode; no extra Python
# packages are needed. The badge is inlined in the HTML, so no web server is
# required.
set -euo pipefail
cd "$(dirname "$0")/.."

python tools/build_guide.py

CHROME=""
for candidate in \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Microsoft/Edge/Application/msedge.exe"
do
  if [ -f "$candidate" ]; then CHROME="$candidate"; break; fi
done

if [ -z "$CHROME" ]; then
  echo "Chrome or Edge not found; open print/guide.html and print to PDF instead." >&2
  exit 1
fi

PROFILE="$(cygpath -w /tmp 2>/dev/null || echo /tmp)/lituk-print"
HTML_URL="file:///$(cygpath -m "$PWD")/print/guide.html"
OUT="$(cygpath -w "$PWD/Life-in-the-UK-Study-Guide.pdf")"

rm -f Life-in-the-UK-Study-Guide.pdf
"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-first-run \
  --no-default-browser-check \
  --user-data-dir="$PROFILE" \
  --no-pdf-header-footer \
  --virtual-time-budget=8000 \
  --print-to-pdf="$OUT" \
  "$HTML_URL" 2>&1 | grep -i "written to file" || true

python - <<'PY'
import re
raw = open("Life-in-the-UK-Study-Guide.pdf", "rb").read()
pages = len(re.findall(rb"/Type\s*/Page[^s]", raw))
print(f"Life-in-the-UK-Study-Guide.pdf: {pages} pages, {len(raw)/1024:.0f} KiB")
PY
