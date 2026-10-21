#!/usr/bin/env python3
"""Static checks for the standalone RegEx Studio browser workspace."""
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "index.html"


class DocumentInspector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])


def main():
    html = SOURCE.read_text(encoding="utf-8")
    inspector = DocumentInspector()
    inspector.feed(html)
    duplicates = sorted({item for item in inspector.ids if inspector.ids.count(item) > 1})
    if duplicates:
        raise SystemExit("Duplicate element IDs: " + ", ".join(duplicates))
    ids = set(inspector.ids)
    references = set(re.findall(r'\$\("([^"]+)"\)', html))
    missing = sorted(references - ids)
    if missing:
        raise SystemExit("Missing IDs referenced by JavaScript: " + ", ".join(missing))

    required = {
        "pattern", "test", "replacement", "compile", "native", "run",
        "accountDialog", "accountForm", "accountOpen", "logoutButton",
        "userWorkspace", "savedName", "savePattern", "patternSearch",
        "favoritesOnly", "savedList",
    }
    missing_required = sorted(required - ids)
    if missing_required:
        raise SystemExit("Required UI elements missing: " + ", ".join(missing_required))

    scripts = re.findall(r"<script(?:\s[^>]*)?>([\s\S]*?)</script\s*>", html, re.I)
    if not scripts:
        raise SystemExit("No inline JavaScript was found")
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required for JavaScript syntax verification")
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as temp:
        temp.write("\n;\n".join(scripts))
        filename = temp.name
    try:
        result = subprocess.run([node, "--check", filename], capture_output=True, text=True, check=False)
        if result.returncode:
            raise SystemExit("JavaScript syntax check failed:\n" + result.stderr)
    finally:
        Path(filename).unlink(missing_ok=True)

    for marker in (
        "prefers-reduced-motion", "IntersectionObserver", "traceMatched",
        'title="Zero-width match"', "/api/v1/auth/register/", "/api/v1/patterns/",
    ):
        if marker not in html:
            raise SystemExit("Expected frontend feature is missing: " + marker)
    print(f"Frontend checks passed: {len(ids)} unique IDs, {len(references)} static JS ID references, JavaScript syntax valid.")


if __name__ == "__main__":
    main()
